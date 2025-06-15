import psycopg2 as pg
from psycopg2 import pool

# In a real production app, get these from config
DB_HOST = "localhost"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_NAME = "lvxin"
DB_PORT = 5432

try:
    connection_pool = pool.SimpleConnectionPool(
        1,  # minconn
        20, # maxconn
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )
    if connection_pool:
        print("Database connection pool created successfully")

except (Exception, pg.DatabaseError) as error:
    print("Error while connecting to PostgreSQL", error)


def get_db_connection():
    """
    Get a connection from the pool.
    Note: Connections must be returned to the pool using `release_db_connection`.
    """
    return connection_pool.getconn()

def release_db_connection(conn):
    """
    Return a connection to the pool.
    """
    connection_pool.putconn(conn)

def close_all_connections():
    """
    Close all connections in the pool.
    """
    if connection_pool:
        connection_pool.closeall()
        print("PostgreSQL connection pool is closed")
