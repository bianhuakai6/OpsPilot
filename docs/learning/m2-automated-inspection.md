# M2 自动化巡检

## 巡检解决什么问题

健康检查只能回答“接口现在能不能响应”。巡检进一步回答“关键依赖是否可用、当前风险是什么、证据在哪里、建议怎么处理”。它是后续运维控制台和 Agent 分析的输入。

## 当前接口

```text
POST /api/v1/inspections/run
```

最近结果也可以通过 `GET /api/v1/inspections/history` 查询。MySQL 模式将报告与明细持久化，应用重启后仍可读取；内存模式只保留当前进程最近 20 次，重启后清空。详见 [巡检历史持久化](m2-inspection-history-persistence.md)。

这是只读操作，不修改活动、预约、MySQL 或 Redis 数据。每次返回 `inspection_id`、整体 `status`、`checked_at` 和 `checks`。每项结果固定包含 `check_id`、`status`、`severity`、`evidence`、`recommendation`。

当前检查项：

- `process_liveness`：应用能响应巡检请求；
- `configuration_integrity`：检查存储模式、启用依赖所需连接串和端口范围；
- `metrics_registry`：确认 Prometheus 指标注册表可读取且包含 OpsPilot HTTP 请求指标；
- `disk_space`：读取系统盘可用空间，可用比例低于 10% 标记为 critical；
- `memory_available`：读取主机可用内存，可用比例低于 10% 标记为 critical；
- `mysql_connectivity`：MySQL 模式下执行 `SELECT 1`，未启用时标记 `skipped`；
- `redis_connectivity`：Redis 启用时执行 `PING`，未启用时标记 `skipped`。

配置检查只校验少量关键字段是否自洽，依赖连通性由独立检查项负责。指标检查也不等于已经配置 Prometheus 服务端、告警规则或长期存储。

资源检查只读系统信息，不会清理磁盘、杀进程或调整内存。Windows 使用系统内存 API，类 Unix 系统使用 `sysconf`；平台不支持或权限不足时返回 `skipped`，避免把“无法采集”误报成“资源耗尽”。10% 是本地演示阈值，生产环境应结合机器规格、业务基线和告警窗口调整。

## 为什么不让巡检自动修复

巡检的第一职责是提供可信证据。自动重启、删除缓存或修改配置属于高风险动作，应在后续 Agent 阶段增加权限、审批和审计，不在基础巡检中偷偷执行。

## 验收方式

启动服务后，在 `/docs` 执行 `POST /api/v1/inspections/run`，或使用：

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/inspections/run
```

内存模式下数据库和 Redis 会显示 `skipped`；MySQL/Redis 启用后会显示实际连接证据。未来控制台可以按 `severity` 和 `status` 展示风险，Agent 可以基于 `evidence` 生成分析，而不是凭空猜测。
