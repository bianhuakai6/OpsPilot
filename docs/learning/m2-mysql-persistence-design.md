# M2 MySQL 持久化设计

## 1. 当前问题与本阶段目标

当前 `app/store.py` 把活动、预约和幂等记录保存在 Python 进程内存中。服务重启后数据会丢失；如果启动多个服务进程，每个进程还会各自持有一份状态。内存锁也只能保护单个进程里的线程。

本设计明确后续 MySQL 实现边界：让活动和预约数据在重启后保留，并通过数据库事务和唯一约束保证多请求、多进程下的正确性。本文件是设计，不表示数据库已连接或已验收。

## 2. 目标数据模型

```text
activities  1 ───── 多  reservations
                         
idempotency_records 独立保存每个逻辑请求的最终结果
```

### activities：活动及容量

| 字段 | 类型建议 | 用途 |
|---|---|---|
| `activity_id` | `VARCHAR(64)` 主键 | 活动标识 |
| `name` | `VARCHAR(200)` | 显示名称 |
| `starts_at` / `ends_at` | `DATETIME(6)` | UTC 时间边界 |
| `capacity` | `INT UNSIGNED` | 总容量 |
| `reserved_count` | `INT UNSIGNED` | 已成功预约数 |
| `created_at` / `updated_at` | `DATETIME(6)` | 审计时间 |

剩余名额由 `capacity - reserved_count` 得出。保存计数是为了能够用一条条件更新原子地竞争名额，而不是先在应用中读取再写回。

### reservations：成功预约

| 字段 | 类型建议 | 用途 |
|---|---|---|
| `reservation_id` | `BIGINT UNSIGNED` 主键 | 数据库生成的预约记录 ID |
| `activity_id` | `VARCHAR(64)` 外键 | 所属活动 |
| `user_id` | `VARCHAR(64)` | 预约用户 |
| `created_at` | `DATETIME(6)` | 创建时间 |

建立唯一约束 `UNIQUE(activity_id, user_id)`，由数据库保证一个用户不能重复预约同一活动。应用层检查仍可用于生成友好错误，但它不能替代数据库约束，因为并发请求可能同时通过应用层检查。

### idempotency_records：请求幂等结果

| 字段 | 类型建议 | 用途 |
|---|---|---|
| `activity_id` | `VARCHAR(64)` | 请求作用的活动 |
| `idempotency_key` | `VARCHAR(128)` | 客户端重试标识 |
| `request_fingerprint` | `CHAR(64)` | 绑定规范化后的请求内容 |
| `http_status` | `SMALLINT UNSIGNED` | 首次请求状态码 |
| `response_json` | `JSON` | 首次成功响应 |
| `created_at` | `DATETIME(6)` | 创建时间 |

使用 `PRIMARY KEY(activity_id, idempotency_key)` 防止同一活动重复创建同一个幂等请求。指纹用于判断相同 key 是否被用于不同请求；不能只凭 key 就把另一种请求的结果返回给调用方。

## 3. 预约事务流程

一次成功预约必须在同一个 InnoDB 事务内完成：

1. 开启事务。
2. 检查活动存在、处于开放时间且允许预约。
3. 用条件更新原子占用一个名额：仅当 `reserved_count < capacity` 时加一。
4. 插入预约记录；唯一约束处理同用户并发重复预约。
5. 插入幂等记录和响应结果；主键处理相同幂等键的并发竞争。
6. 全部成功后提交事务，并返回 `201`。
7. 任意步骤失败则回滚，容量计数、预约记录和幂等记录一起撤销。

关键 SQL 的意图：

```sql
UPDATE activities
SET reserved_count = reserved_count + 1,
    updated_at = UTC_TIMESTAMP(6)
WHERE activity_id = :activity_id
  AND reserved_count < capacity
  AND starts_at <= UTC_TIMESTAMP(6)
  AND ends_at > UTC_TIMESTAMP(6);
```

应用检查受影响行数：为 `1` 表示原子占位成功；为 `0` 表示活动不存在、未开放或没有名额，需要再读取活动状态以返回稳定错误码。具体的失败分类查询也必须处于明确的事务边界中。

## 4. 并发与幂等边界

- **不超卖**：条件 `UPDATE` 由 InnoDB 加锁并原子判断容量，不能用“先 SELECT 容量、应用里加一、再 UPDATE”的无锁流程。
- **不重复预约**：`UNIQUE(activity_id, user_id)` 是最终数据约束；并发冲突后回滚整笔事务。
- **重试不重复执行**：幂等记录在同一事务提交。相同 key 和相同请求应读取并返回已保存响应；相同 key 对应不同请求则返回 `409`。
- **竞态处理**：并发请求可能在写入唯一键时遇到重复键异常。实现需要回滚当前事务，再读取已提交的幂等记录并比较指纹；不能吞掉数据库异常后继续复用已变更的事务。
- **数据库不可用**：请求应失败并记录可诊断日志；不能退回到各进程各自的内存状态，否则会制造看似成功但实际不一致的数据。

## 5. 从现有代码迁移的边界

当前 API 路径和响应格式保持不变。后续实现会把路由中的直接状态访问替换成服务层/存储层调用：

```text
app/routes/activities.py
    -> 预约服务逻辑
        -> MySQL 事务与数据访问
```

`app/store.py` 的进程内字典和 `Lock` 在 MySQL 版本验收后移除。`reset_state()` 只用于测试夹具或测试数据库初始化，不应成为生产接口。

## 6. 验收计划

MySQL 实际集成至少需要验证：

1. 应用重启后活动和预约数据仍存在。
2. 多线程并发预约容量为 2 的活动，恰好 2 个成功，其余得到容量耗尽错误。
3. 同一用户并发提交不同幂等键，最终只能有一条预约记录。
4. 同一幂等键重试返回完全相同的成功结果，数据库只产生一条预约。
5. 同一幂等键绑定不同请求时返回冲突。
6. 在事务中模拟后续写入失败，确认容量计数和预约记录均回滚。
7. 数据库不可用时健康/就绪状态准确反映依赖问题，不把存活检查误当成就绪检查。

## 7. 环境与依赖决策

仓库计划使用 MySQL 8。应用数据访问层优先采用 SQLAlchemy 2.x；具体同步或异步驱动在接入前结合当前 FastAPI 同步路由与教学复杂度确认，并记录选择理由。密码和连接串通过环境变量或本地未提交的 `.env` 提供，禁止进入 Git。

当前 Docker CLI 可用，但 Docker Engine 未运行，因此尚不能启动 MySQL 容器并做真实集成测试。开始数据库实现前，先启动 Docker Desktop 并确认 `docker info` 能读取 Server 信息；随后用 Compose 启动 MySQL，完成上述验收。未经真实容器测试，不把持久化能力标记为完成。

## 8. 学习与面试复盘

需要能解释：

- 为什么应用层“先查再写”无法防止并发超卖？
- 条件更新、唯一约束和事务分别解决什么问题？
- 如果预约插入成功但幂等记录写入失败，为什么必须整体回滚？
- 为什么多副本部署不能依赖 Python `Lock`？
- 为什么存活检查和数据库就绪检查应该区分？
