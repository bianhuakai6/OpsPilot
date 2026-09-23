# M1 接口和数据模型草案

## 1. 接口

### 查询活动

`GET /api/v1/activities/{activity_id}`

成功响应至少包含：活动 ID、状态、总名额、剩余名额、开始时间和结束时间。

### 提交预约

`POST /api/v1/activities/{activity_id}/reservations`

请求体第一版使用：

```json
{
  "user_id": "user-001"
}
```

请求头必须包含 `Idempotency-Key`。客户端因超时重试时，应复用同一个键和相同请求体；服务返回首次成功的结果，不重复扣减名额。相同键被用于不同用户时返回 `idempotency_key_conflict`。

成功返回预约结果。用户用新幂等键重复预约、活动未开始、活动结束和名额已满时返回稳定的业务错误码。

## 2. 错误分类

| 情况 | HTTP 状态 | 业务含义 |
|---|---:|---|
| 参数非法 | 400 | 客户端请求不符合接口约定 |
| 活动不存在 | 404 | 资源不存在 |
| 活动状态不允许预约 | 409 | 当前业务状态不允许操作 |
| 新请求重复预约 | 409 | 用户已经预约 |
| 幂等键用于不同请求 | 409 | 幂等键冲突 |
| 名额已满 | 409 | 业务资源耗尽 |
| 服务内部异常 | 500 | 需要排查系统或依赖 |
| 缺少幂等键或请求格式错误 | 422 | 请求未通过接口校验 |

## 3. 第一版数据模型

M1 先使用内存数据结构完成接口和规则验证，不把数据库细节与业务规则混在第一步。M1 验收后再在 M2 引入持久化。

逻辑实体：

- `Activity`：活动状态和名额；
- `Reservation`：用户与活动的成功预约关系。

数据库阶段的表约束草案：

```sql
CREATE TABLE activities (
    activity_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    starts_at DATETIME(6) NOT NULL,
    ends_at DATETIME(6) NOT NULL,
    capacity INT NOT NULL,
    CHECK (capacity >= 0)
);

CREATE TABLE reservations (
    reservation_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    activity_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    UNIQUE KEY uq_activity_user (activity_id, user_id),
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
);

CREATE TABLE idempotency_records (
    activity_id VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    response_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (activity_id, idempotency_key)
);
```

此草案说明持久化需要的唯一性约束，不代表 M1 已连接或验证数据库。并发扣减名额的事务设计留到 M2 实际实现和测试。

## 4. 幂等设计草案

业务唯一性以 `(activity_id, user_id)` 保证；请求重试结果以 `(activity_id, idempotency_key)` 保存。后续进入数据库时，应分别用唯一约束保证业务唯一性和幂等键唯一性，不能只依赖应用层查询。

内存版本用单进程锁保护“查状态、检查名额、写入记录”这个临界区，仅用于学习和单进程实验。多进程/多副本的生产实现必须交由数据库事务和唯一约束协调。

## 5. M1 验收场景

- 查询存在的活动；
- 查询不存在的活动；
- 正常预约；
- 同一用户使用新键重复预约；
- 同一请求使用相同键重试并得到原成功结果；
- 相同幂等键用于不同用户时拒绝；
- 并发请求不能超过名额；
- 预约后名额耗尽；
- 未开始或已结束活动预约；
- 非法请求体；
- 校验缺少幂等键时请求被拒绝。
