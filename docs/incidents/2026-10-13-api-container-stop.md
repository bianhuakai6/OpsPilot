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

- 这次操作验证了人工停止后的手动恢复流程，不等于验证了意外进程崩溃后的自动重启。
- `unless-stopped` 可处理容器进程退出等由 Docker 观察到的异常退出，但人工停止会抑制重启策略；真实生产自愈还需用 Kubernetes 控制器或明确的进程故障注入进一步验证。
- 未修改 MySQL、Redis、数据卷或预约数据。服务中断期间没有执行业务写请求。
- 后续行动：在可控测试容器中设计可重复的非人工退出注入，并分别验证容器重启与健康检查恢复；当前不把自动恢复写为已验收能力。
