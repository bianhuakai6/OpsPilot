# M2 自动化巡检

## 巡检解决什么问题

健康检查只能回答“接口现在能不能响应”。巡检进一步回答“关键依赖是否可用、当前风险是什么、证据在哪里、建议怎么处理”。它是后续运维控制台和 Agent 分析的输入。

## 当前接口

```text
POST /api/v1/inspections/run
```

这是只读操作，不修改活动、预约、MySQL 或 Redis 数据。每次返回 `inspection_id`、整体 `status`、`checked_at` 和 `checks`。每项结果固定包含 `check_id`、`status`、`severity`、`evidence`、`recommendation`。

当前检查项：

- `process_liveness`：应用能响应巡检请求；
- `mysql_connectivity`：MySQL 模式下执行 `SELECT 1`，未启用时标记 `skipped`；
- `redis_connectivity`：Redis 启用时执行 `PING`，未启用时标记 `skipped`。

## 为什么不让巡检自动修复

巡检的第一职责是提供可信证据。自动重启、删除缓存或修改配置属于高风险动作，应在后续 Agent 阶段增加权限、审批和审计，不在基础巡检中偷偷执行。

## 验收方式

启动服务后，在 `/docs` 执行 `POST /api/v1/inspections/run`，或使用：

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/inspections/run
```

内存模式下数据库和 Redis 会显示 `skipped`；MySQL/Redis 启用后会显示实际连接证据。未来控制台可以按 `severity` 和 `status` 展示风险，Agent 可以基于 `evidence` 生成分析，而不是凭空猜测。
