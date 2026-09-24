# Redis 基础知识与 OpsPilot 实践

## 1. Redis 是什么

Redis 是一个高性能的内存数据存储系统，常用来保存短期、高频访问或需要快速协调的数据。它以键值为基础，也支持 Hash、List、Set、Sorted Set 和 Stream 等数据结构。

最简单的操作是：

```text
SET service:status healthy
GET service:status
```

Redis 主要把数据放在内存中，因此读写延迟低。它可以通过 RDB 或 AOF 持久化数据，但这不意味着它自动等同于 MySQL 的核心业务数据库。是否可靠，取决于持久化、过期、复制和故障恢复配置。

## 2. Redis 与 MySQL 的职责区别

```text
MySQL：长期业务事实、事务、唯一约束、复杂查询
Redis：缓存、计数器、限流、临时状态、快速协调
```

本项目的预约记录需要重启后保留，并且依赖唯一约束和事务回滚，因此放在 MySQL。Redis 不替代 `reservations` 表，也不替代活动容量的数据库约束。

## 3. 常见数据结构

| 类型 | 示例 | 常见用途 |
|---|---|---|
| String | `SET key value` | 缓存、状态、计数器 |
| Hash | `HSET service status healthy` | 对象字段 |
| List | `LPUSH task-queue task-001` | 简单队列 |
| Set | `SADD instances pod-1 pod-2` | 去重集合 |
| Sorted Set | `ZADD latency 120 request-1` | 排行、优先级、时间排序 |
| Stream | `XADD alerts * severity critical` | 事件流和消费记录 |

实际选择结构时，要先明确数据生命周期、并发方式、是否允许丢失和读取模式，不能只因为 Redis 快就把所有数据放进去。

## 4. Redis 常见应用场景

### 缓存

先读 Redis，未命中再查 MySQL，并设置过期时间。写入 MySQL 成功后需要删除或更新缓存，否则会读到旧数据。

### 限流

使用带过期时间的计数器统计用户或接口在时间窗口内的请求次数，超过阈值返回 `429`。

### 分布式锁

多个服务副本争抢同一个任务时，用带过期时间的锁让一个实例执行。锁不是最终一致性保证，业务仍需要数据库约束或幂等设计兜底。

### 临时任务状态

把巡检任务的 `queued/running/succeeded/failed` 状态保存一段时间，供控制台查询，完成后自动过期。

### 会话和短期凭证

保存会话与用户的映射，并通过 TTL 自动过期。敏感信息需要额外的安全设计。

## 5. Redis 在本项目的代码位置

### 容器基础设施

`docker-compose.yml` 使用 `redis:7.4`，映射宿主机 `6379` 端口，启用 AOF，并配置 `redis-cli ping` 健康检查。

### 运行配置

`app/config.py` 定义：

```python
redis_enabled: bool = False
redis_url: str = "redis://127.0.0.1:6379/0"
```

设置 `OPSPILOT_REDIS_ENABLED=true` 后，`app/runtime.py` 创建 Redis 客户端。

### 连接检查

`app/redis_client.py` 的 `check_redis()` 执行 `client.ping()`。`/readyz` 和 `app/inspection.py` 都调用这个检查：Redis 返回 `PONG` 才算可用。

### 当前没有做的事情

当前 Redis 尚未用于：

- 预约缓存；
- 限流；
- 分布式锁；
- 任务队列；
- Agent 上下文存储。

这些能力需要分别设计过期时间、一致性、故障降级、权限和审计，不能把“容器启动成功”描述成“缓存或限流已经完成”。

## 6. 当前请求中的 Redis 链路

```text
控制台或客户端
  -> GET /readyz 或 POST /api/v1/inspections/run
  -> app/routes/health.py 或 app/inspection.py
  -> app/redis_client.py
  -> Redis PING
  -> Redis 返回 PONG
  -> API 返回 ready/pass
  -> 控制台展示 Redis 正常
```

因此当前 Redis 的真实作用是：作为可选依赖被探测，并把依赖可用性纳入就绪检查和自动化巡检。

## 7. 故障场景与排查

| 现象 | 可能原因 | 首要检查 |
|---|---|---|
| 容器不是 `healthy` | Redis 未启动或健康检查失败 | `docker compose ps`、`redis-cli ping` |
| `/readyz` 返回 `redis_unavailable` | 地址、端口或网络错误 | `OPSPILOT_REDIS_URL`、6379 监听状态 |
| 缓存读到旧数据 | 缓存失效策略缺失 | 写入流程和 TTL |
| 锁长期不释放 | 没有过期时间或进程异常 | 锁 TTL、持有者标识、恢复流程 |
| Redis 重启后临时数据消失 | 数据本来未持久化或只允许丢失 | AOF/RDB 和业务降级设计 |

## 8. 面试表达练习

> 我在项目中用 Docker 部署 Redis 7.4，并通过配置开关接入 FastAPI 的就绪检查和自动化巡检。当前预约事实仍由 MySQL 通过事务和唯一约束保证，Redis 只承担可选依赖探测；后续会根据明确的一致性和降级策略引入限流、缓存或分布式任务协调，而不是把 Redis 当作 MySQL 的替代品。

## 9. 自测问题

1. 为什么预约事实放 MySQL 而不是直接放 Redis？
2. Redis 的 `PING/PONG` 能证明什么，不能证明什么？
3. 缓存更新成功后为什么还需要处理缓存失效？
4. 分布式锁为什么必须设置过期时间？
5. Redis 容器 healthy 是否等价于业务已经正确使用 Redis？
