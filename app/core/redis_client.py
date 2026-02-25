from redis import Redis
from app import settings

redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True
)