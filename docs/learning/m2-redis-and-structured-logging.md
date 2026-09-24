# M2 Redis 与结构化日志

## Redis 的作用

MySQL 保存长期业务事实，Redis 适合短期、高频、低延迟数据。当前阶段 Redis 已作为可选依赖接入容器和 `/readyz` 检查，但预约主数据仍由 MySQL 负责，避免 MySQL 与 Redis 双写造成不一致。

后续可以在有明确一致性方案后使用 Redis 做幂等热点缓存、限流计数、短期任务状态或分布式协调。Redis 不替代数据库唯一约束和事务。

## 结构化日志的作用

日志不再只是一段人类文本，而是 JSON 字段：

```json
{"level":"INFO","logger":"opspilot","message":"http_request","request_id":"...","method":"GET","path":"/healthz","status_code":200,"duration_ms":2.1}
```

请求中可以携带 `X-Request-ID`；如果没有，服务会生成一个，并在响应头中返回。这样一次请求可以在网关、应用日志和后续 Agent 分析中关联起来。

当前记录字段：

- `request_id`：请求关联标识；
- `method`、`path`：请求目标；
- `status_code`：结果；
- `duration_ms`：应用处理耗时。

下一阶段可在此基础上增加错误堆栈、用户/租户标识、数据库耗时和发布版本，但敏感信息不能直接写入日志。
