# Redis 本地基础设施

## Redis 在项目中的定位

MySQL 保存需要长期可靠保留的业务数据；Redis 适合保存短期、热点或需要快速读写的数据。当前阶段只接入 Redis 的容器和就绪检查，还没有把预约主数据迁移到 Redis，避免出现 MySQL 与 Redis 双写不一致。

后续可选择的用途包括幂等热点缓存、限流计数、短期任务状态和分布式锁。每种用途都需要单独定义过期时间、故障降级和一致性边界。

## 启动与检查

```powershell
docker compose up -d redis
docker compose ps
docker compose exec redis redis-cli ping
```

看到 `PONG` 且容器为 `healthy`，说明 Redis 容器基础设施正常。

启用 API 的 Redis 就绪检查：

```powershell
$env:OPSPILOT_REDIS_ENABLED = "true"
$env:OPSPILOT_REDIS_URL = "redis://127.0.0.1:6379/0"
$env:OPSPILOT_PORT = "8004"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8004
```

访问 `http://127.0.0.1:8004/readyz`。Redis 不可用时应返回 `503` 和 `redis_unavailable`；未启用时不会影响默认模式。

## 为什么不直接把预约写进 Redis

预约记录需要持久化、唯一约束和事务回滚，当前由 MySQL 负责。Redis 作为缓存或协调组件不能替代 MySQL 的事实数据职责。后续如果引入分布式锁，也必须保留数据库唯一约束作为最终防线。
