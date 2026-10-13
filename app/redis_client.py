import redis


def create_redis_client(url: str) -> redis.Redis:
    """创建 Redis 客户端；探测和业务命令都必须有界等待。"""
    return redis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def check_redis(client: redis.Redis) -> bool:
    return client.ping()
