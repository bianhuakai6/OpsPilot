# M4：巡检异常与告警事件关联

## 事件是怎么产生的

每次 `POST /api/v1/inspections/run` 执行后，系统把巡检项交给 `InspectionAlertStore`：

- 检查状态为 `fail`：按 `check_id` 创建告警，保存严重级别、证据、建议和来源 `inspection_id`；
- 同一个检查再次失败：复用同一个 `alert_id`，更新时间和证据，并增加 `occurrences`；
- 检查恢复为 `pass`：把原告警标记为 `resolved`，保存恢复巡检的 ID 和时间；
- 检查为 `skipped`：不据此自动关闭告警，因为这代表“没检查”，不是“确认恢复”。

查看接口：

```text
GET /api/v1/alerts
```

服务概览页会显示当前 open 告警、最近证据、出现次数和处理建议。演练中停止 Redis 后，巡检应生成 Redis open 告警；恢复 Redis 并再次巡检后，同一事件应变成 resolved，而不是新建一条无关事件。

真实容器验收：镜像 `opspilot:0.1.0-7be8074` 下停止 Redis 后生成 `alert-4b9e7be0-e129-47b5-85ea-a8dd900bd34c`，来源巡检为 `inspection-20261013T081511361891Z`；启动 Redis 后的下一次巡检把同一事件标为 resolved，来源更新为 `inspection-20261013T081601434014Z`。API、MySQL、Redis 均恢复 healthy。

## 当前边界

事件保存在应用进程内存，服务重启后清空；这是本地关联实验，不是持久化告警系统，也没有 Prometheus Alertmanager、通知渠道、值班路由、RBAC 或审批。真实生产方案需要将事件持久化，并补充告警抑制、分组、通知与审计策略。
