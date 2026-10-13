# 受限只读流量演练复盘

## 基本信息

- 演练时间：2026-10-13 16:03（Asia/Shanghai）
- 目标：`GET /api/v1/activities/activity-001`
- 环境：本机 Docker Desktop，API、MySQL、Redis Compose 服务

## 负载与结果

- 参数：10 秒、4 个并发 worker；符合界面最多 30 秒、最多 8 并发的安全限制。
- 请求数：4,441；成功 4,441；失败 0；吞吐量约 443.61 req/s。
- 压测器延迟：P50 8.27ms、P95 12.38ms、最大 43.75ms。
- SLO 快照：pass；累计业务请求 4,441，5xx 为 0，可用性 100%，Histogram bucket 近似 P95 为 10ms。
- API、MySQL、Redis 在演练后均为 healthy。
- 压测请求通过专用请求头抑制逐条访问日志，没有产生逐请求日志洪峰。

## 结论与边界

- 该参数下本机服务能够稳定完成只读查询，SLO 统计和压测器结果方向一致；P95 数值存在差异，因为压测器用实际样本最近秩计算，而 SLO 使用 Prometheus Histogram bucket 近似值。
- 这不是生产容量结论。结果受本机硬件、Docker Desktop、单实例和短时请求分布影响，不能直接换算为云上容量或用户规模。
- 后续可逐档增加并发，并记录错误率、P95、资源和 MySQL 连接池指标；每次测试仍需遵守限流边界，避免压垮开发机。
