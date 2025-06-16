import os
import shutil
import psycopg2
import psycopg2.extras
from datetime import datetime
import logging

# This assumes your core.database is accessible from this script's location.
# You might need to adjust the Python path if you run this from a different directory.
# For example, by setting PYTHONPATH=.
try:
    from core.database import get_db_connection, release_db_connection
except ImportError:
    print("Could not import from core.database. Make sure PYTHONPATH is set correctly.")
    print("Example: export PYTHONPATH=/path/to/your/project")
    exit(1)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def cleanup_expired_uploads():
    """
    Finds and deletes expired, in-progress upload sessions and their associated temporary files.
    An upload is considered expired if it is still 'in_progress' and its 'expires_at'
    timestamp is in the past.
    """
    conn = None
    cleaned_sessions = 0
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Could not get a database connection for the cleanup job.")
            return

        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Select sessions that are 'in_progress' and have expired.
            # We lock the rows to prevent other processes from modifying them while we clean up.
            cur.execute(
                """
                SELECT id, storage_path FROM file_upload_sessions
                WHERE status = 'in_progress' AND expires_at < %s
                FOR UPDATE SKIP LOCKED
                """,
                (datetime.utcnow(),)
            )
            expired_sessions = cur.fetchall()

            if not expired_sessions:
                logger.info("No expired uploads to clean up.")
                return

            logger.info(f"Found {len(expired_sessions)} expired uploads to clean up.")

            for session in expired_sessions:
                upload_id = session['id']
                storage_path = session['storage_path']

                # Step 1: Delete temporary files from the filesystem
                if storage_path and os.path.isdir(storage_path):
                    try:
                        shutil.rmtree(storage_path)
                        logger.info(f"Successfully deleted temporary directory: {storage_path}")
                    except OSError as e:
                        logger.error(f"Error deleting directory {storage_path} for session {upload_id}: {e}")
                        # If we can't delete the files, we skip this session
                        # and don't delete the DB record to allow for manual intervention.
                        continue

                # Step 2: Delete the record from the database
                cur.execute("DELETE FROM file_upload_sessions WHERE id = %s", (upload_id,))
                cleaned_sessions += 1

        conn.commit()
        if cleaned_sessions > 0:
            logger.info(f"Successfully cleaned up {cleaned_sessions} expired upload session(s).")

    except Exception as e:
        logger.error(f"An error occurred during the upload cleanup process: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_db_connection(conn)

if __name__ == "__main__":
    logger.info("Starting the cleanup job for expired uploads...")
    cleanup_expired_uploads()
    logger.info("Cleanup job finished.") 