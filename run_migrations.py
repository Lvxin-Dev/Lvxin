import os
import logging
from psycopg2 import sql, connect
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_db_connection():
    """Create a database connection."""
    return connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", 5432)
    )

def get_migration_files():
    """Get all migration files in the migrations directory, sorted by name."""
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    if not os.path.exists(migrations_dir):
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return []
    
    migration_files = [
        f for f in os.listdir(migrations_dir)
        if f.endswith(".sql") and f != "__init__.py"
    ]
    migration_files.sort()
    return [os.path.join(migrations_dir, f) for f in migration_files]

def get_applied_migrations(conn):
    """Get a set of already applied migration filenames."""
    with conn.cursor() as cur:
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            
            cur.execute("SELECT filename FROM migrations")
            return {row[0] for row in cur.fetchall()}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error getting applied migrations: {e}")
            return set()

def apply_migration(conn, migration_file):
    """Apply a single migration file."""
    filename = os.path.basename(migration_file)
    logger.info(f"Applying migration: {filename}")
    
    try:
        with open(migration_file, 'r') as f:
            sql_script = f.read()
        
        with conn.cursor() as cur:
            # Execute the migration
            cur.execute(sql_script)
            
            # Record the migration
            cur.execute(
                "INSERT INTO migrations (filename) VALUES (%s)",
                (filename,)
            )
            
            conn.commit()
            logger.info(f"Successfully applied migration: {filename}")
            return True
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error applying migration {filename}: {e}")
        return False

def main():
    """Run all pending migrations."""
    logger.info("Starting database migrations...")
    
    try:
        # Get database connection
        conn = get_db_connection()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Get applied and pending migrations
        applied_migrations = get_applied_migrations(conn)
        all_migrations = get_migration_files()
        
        # Apply pending migrations
        for migration_file in all_migrations:
            filename = os.path.basename(migration_file)
            if filename not in applied_migrations:
                if not apply_migration(conn, migration_file):
                    logger.error(f"Migration failed: {filename}")
                    return 1
        
        logger.info("All migrations completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        return 1
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    exit(main())
