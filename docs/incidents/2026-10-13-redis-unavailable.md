# Redis 不可用演练复盘

## 基本信息

- 演练时间：2026-10-13 15:35（Asia/Shanghai）
- 故障对象：本地 Compose 服务 `opspilot-redis`
- 演练环境：Windows 宿主机 + Docker Desktop，本地 OpsPilot 容器
- 影响范围：就绪探针和只读巡检；未向预约接口发送写请求，MySQL 与数据卷未修改

## 目标与注入

- 验证目标：确认 Redis 不可用时探针及时失败、巡检保留证据，恢复后服务重新就绪。
- 故障注入：执行 `docker stop opspilot-redis`，保持 API 和 MySQL 运行。
- 预期信号：`/readyz` 返回 503；巡检报告中 `redis_connectivity` 为 fail。

## 观测证据

- 故障窗口 `/readyz` 返回 HTTP 503，错误码 `redis_unavailable`，实测耗时约 4.3 秒。
- `POST /api/v1/inspections/run` 返回 HTTP 200 的巡检报告，整体状态为 fail；Redis 项为 fail/warning，证据为 `ConnectionError`，建议检查 Redis 容器、URL 和端口。
- 首次预演在旧运行镜像上发现 Redis 客户端没有连接/命令超时，探测可能长时间等待。为保护演练窗口，立即重启 Redis；未发生数据删除。

## 恢复过程

- 恢复动作：执行 `docker start opspilot-redis`，等待 Docker healthcheck。
- 恢复验证：Redis 为 healthy；`/readyz` 返回 ready 且 MySQL、Redis 均 connected；新巡检整体 pass，Redis 项 pass。
- 数据影响：只停止并启动 Redis 容器，没有删除容器或数据卷；MySQL 始终 healthy。

## 根因与改进

- 根因：Redis 客户端默认没有连接和命令超时，依赖探测的等待时间没有上界。
- 已完成：Redis 客户端设置 2 秒连接超时和 2 秒 socket 超时；部署 `opspilot:0.1.0-dc2f89c` 后复测，故障探针在 6 秒调用上限内返回 503，巡检按预期标记 Redis 故障。
- 演练还发现：健康探针会混入业务 SLO 指标。现将 SLO 统计限定到 `/api/v1/activities/...`，排除健康检查、巡检和静态页面。
- 后续改进：增加 MySQL 慢查询和 API 容器异常演练；扩展 SLO 为可查询时间窗口，并增加至少三份演练复盘。
- 尚未覆盖：Redis 是依赖检查项，当前业务路径没有把 Redis 用作缓存或预约数据存储；因此该演练证明的是就绪状态诊断，不是 Redis 故障下的业务降级能力。
