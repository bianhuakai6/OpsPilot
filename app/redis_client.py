import redis


def create_redis_client(url: str) -> redis.Redis:
    """创建 Redis 客户端；连接在真正执行检查或命令时建立。"""
    return redis.Redis.from_url(url, decode_responses=True)


def check_redis(client: redis.Redis) -> bool:
    return client.ping()
