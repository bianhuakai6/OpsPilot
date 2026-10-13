# M4：故障演练与 SLO 阶段验收

## 本阶段解决的问题

此前系统能查看健康状态，却没有量化可靠性目标，也没有通过故障注入证明异常能被发现、恢复能被确认。M4 增加本地 SLO/错误预算快照，演练 Redis、MySQL、慢查询、容器进程退出和受限流量，并把巡检失败关联为告警事件。

## 工作方式

- SLO：`GET /api/v1/slo` 读取 Prometheus 客户端累计指标，仅计入 `/api/v1/activities/...` 业务接口，排除健康探针和运维接口。
- 依赖探测：Redis 和 MySQL 客户端有 2 秒级连接/读写超时；依赖失败时 `/readyz` 返回 503。
- 巡检：产生带状态、证据和建议的结果；MySQL 故障时跳过向同一数据库持久化失败报告，防止二次阻塞。
- 告警关联：失败检查创建/更新 open 事件；相同检查恢复后置为 resolved。当前事件在进程内存中。
- 容器恢复：Compose `unless-stopped` 在 API PID 1 进程异常退出后重启容器；人工 `docker kill` 按操作者停止处理，不会触发自动重启。

## 如何证明

演练记录位于 `docs/incidents/`：

- Redis 停止：就绪探针 503，巡检记录 Redis 失败；恢复后巡检通过。
- MySQL 停止：就绪探针 503；修复后巡检在有限时间内返回 MySQL fail 报告，恢复后通过。
- Redis 告警关联：同一 alert ID 从 open 转为 resolved。
- MySQL 慢日志：只读 `SELECT SLEEP(2)` 被原生慢日志捕获，随后恢复原配置。
- 受限流量：10 秒/4 并发与 30 秒/8 并发只读查询均完成，结果记录请求量、延迟、错误和限制。
- 容器进程：API PID 1 收到 SIGTERM 后自动重启，RestartCount 增加，服务恢复 healthy。

## 尚未实现

- SLO 仍是进程生命周期快照，重启后清零，不是滚动时间窗口或长期服务等级报告。
- P95 使用 Prometheus Histogram bucket 近似计算；要做严谨时序分析还需要 Prometheus Server/Grafana。
- 告警事件尚未持久化，也没有 Alertmanager、通知、值班路由、RBAC 或审批。
- 容器重启不等同 Kubernetes 自愈；没有验证节点故障、多副本、滚动发布或云环境容量。
- 慢查询演练验证的是日志采集，不等同应用请求慢 SQL 与 Trace 的关联分析。

## 测试和运行状态

M4 最后一次代码交付通过宿主机与 Docker 容器测试；本机 API、MySQL、Redis 均为 healthy。演练使用正式镜像标签和本机 `data/release-history.jsonl` 留痕；临时故障容器已回收，正式镜像和业务数据卷保留。
