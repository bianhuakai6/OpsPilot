# API 容器停止与恢复观察

## 基本信息

- 演练时间：2026-10-13 15:43（Asia/Shanghai）
- 对象：`opspilot-api` 容器，镜像 `opspilot:0.1.0-aaf411e`
- 目的：理解 Docker Compose `unless-stopped` 策略遇到人工停止时的行为

## 操作与证据

- 使用 `docker kill opspilot-api` 后，容器退出码为 137，`RestartCount=0`，状态为 exited。
- 容器的 RestartPolicy 是 `unless-stopped`，但 Docker 将人工 kill/stop 视为操作者明确停止，不会因此自动启动。
- 使用 `docker start opspilot-api` 后，容器恢复为 running/healthy，`/readyz` 返回 ready，镜像仍为 `opspilot:0.1.0-aaf411e`。

## 结论与边界

- `docker kill` 属于人工停止操作，Docker 不会自动重启；`docker start` 后服务可恢复。
- 隔离短命容器的进程非零退出实验中，`on-failure:2` 重启计数达到 2；`unless-stopped` 实验中，进程异常退出后容器反复重启，手动停止后结束重启。
- 随后对实际 API 容器 PID 1 发送 `SIGTERM`，Compose 的 `unless-stopped` 自动拉起 API，`RestartCount` 从 0 增至 1；容器恢复 running/healthy，`/readyz` 返回 ready。正式镜像仍为 `opspilot:0.1.0-7be8074`。
- 因此已验证本地容器进程异常退出时 Docker 重启策略生效；这不是 Kubernetes 自愈、节点故障恢复或多副本高可用验收。
- 未修改 MySQL、Redis、数据卷或预约数据。服务中断期间没有执行业务写请求。
- 后续行动：在 Kubernetes 阶段验证 Pod 自愈、readiness/liveness 和滚动更新；当前不能把这些能力写成已完成。
