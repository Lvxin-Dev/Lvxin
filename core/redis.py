import redis.asyncio as redis
import os

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

async def get_redis_connection():
    return redis_client 