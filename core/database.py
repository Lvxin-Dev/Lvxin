import psycopg2 as pg
from psycopg2 import pool
import os
from dotenv import load_dotenv
import redis.asyncio as redis
from core.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD

load_dotenv()

# In a real production app, get these from config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
DB_NAME = os.getenv("DB_NAME", "lvxin")
DB_PORT = os.getenv("DB_PORT", 5432)

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

# --- Redis Connection Pool ---
redis_pool = None
try:
    redis_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        max_connections=20,
        decode_responses=True,
    )
    if redis_pool:
        print("Redis connection pool created successfully")
except Exception as e:
    print(f"Error while connecting to Redis: {e}")

def get_redis_connection():
    """
    Get a Redis connection from the pool.
    """
    if not redis_pool:
        raise ConnectionError("Redis connection pool is not initialized")
    return redis.Redis(connection_pool=redis_pool)

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
    if redis_pool:
        redis_pool.disconnect()
        print("Redis connection pool is closed")
