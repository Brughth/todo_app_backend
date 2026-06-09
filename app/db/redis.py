from redis.asyncio import Redis
from app.core.config import Config


token_blocklist = Redis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=0,
    decode_responses=True,
)


async def add_jti_to_blocklist(jti: str, ttl: int) -> None:
    """
    Add a token JTI to the Redis blocklist.

    Fix 7: ttl is dynamic — equals the remaining lifetime of the token.
    Redis auto-deletes the key after ttl seconds, so no manual cleanup needed.

    Usage:
        exp = token_data["exp"]
        ttl = exp - int(datetime.now(timezone.utc).timestamp())
        if ttl > 0:
            await add_jti_to_blocklist(jti, ttl=ttl)
    """
    await token_blocklist.set(
        name=jti,
        value="revoked",
        ex=ttl,
    )


async def is_token_in_blocklist(jti: str) -> bool:
    """Return True if the JTI has been revoked."""
    value = await token_blocklist.get(jti)
    return value is not None
