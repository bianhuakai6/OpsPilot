# OpsPilot 技术栈规划

## 1. 选型原则

本项目的技术栈服务于 SRE、平台运维和云原生能力，不以堆叠组件数量为目标。

选型遵循：

1. 本地可运行优先；
2. 每个组件有明确问题和验证实验；
3. 先建立闭环，再增加复杂度；
4. 优先选择目标岗位常见技术；
5. 保留替代方案和迁移路径；
6. AI 辅助实现，但关键设计和验证必须由人掌握。

## 2. 分阶段技术栈

| 层次 | M1-M2 本地闭环 | M3-M4 稳定性 | M5 Agent | M6 云原生本地化 | 云阶段 |
|---|---|---|---|---|---|
| API | Python 3.13 + FastAPI | 同左 | Python Agent 服务 | 可拆分控制面 | 视需要迁移部分 Go |
| 数据库 | MySQL 8 | 慢查询、事务实验 | 只读诊断工具 | StatefulSet/外部依赖对比 | 云数据库 |
| 缓存 | Redis 7 | 超时、降级、命中率 | 指标和日志查询 | Service/持久化实验 | 云 Redis |
| 容器 | Docker | 镜像版本和健康检查 | Agent 工具容器化 | Kubernetes | 托管 Kubernetes |
| 编排 | Docker Compose | 发布脚本和回滚 | Agent 权限边界 | kind 或 Docker Desktop Kubernetes | 云 Kubernetes |
| 指标 | Prometheus | SLO、告警规则 | Agent 查询 PromQL | kube-state-metrics | 云监控对比 |
| 看板 | Grafana | 故障看板 | 告警上下文 | 集群/工作负载看板 | 云监控对比 |
| 日志 | JSON stdout | 故障关联 | Agent 日志检索 | Loki/Promtail | 云日志 |
| 测试 | pytest + HTTP 测试 | 故障实验、回归测试 | Agent 评估集 | Kubernetes 验证脚本 | CI 执行 |
| 巡检 | Python 规则检查器 | 依赖、配置、资源和发布状态 | Agent 解释和归因 | 集群资源巡检 | 云资源巡检适配 |
| 压测 | Locust 或 k6 | 固定场景基准 | 告警触发实验 | 扩缩容实验 | 云容量实验 |
| 交付 | Make/PowerShell 脚本 | 发布、回滚 | 工具调用审计 | Helm 或 Kustomize | Terraform/OpenTofu |
| Agent | 暂不引入 | 暂不引入 | LLM API + 工具调用 + Runbook | 读取 Kubernetes 只读信息 | 云资源工具适配 |

## 3. 第一版冻结栈

M1-M2 只使用：Python 3.13、FastAPI、pytest、SQLAlchemy、MySQL 8、Redis 7、Docker Compose、Prometheus、Grafana 和 JSON 结构化日志。

第一版不引入 Kubernetes、消息队列、链路追踪和 Agent，先证明业务请求、数据依赖、指标、基础巡检和容器运行闭环。

## 4. 为什么从 Python 开始

Python 是当前阶段的学习杠杆，不代表最终必须使用 Python 完成所有服务：

- 将注意力集中在 HTTP、数据库、缓存、监控和故障处理；
- 适合自动化、平台脚本和 Agent 编排；
- FastAPI 提供类型标注、接口文档和清晰的服务结构；
- 后续选择一个组件迁移到 Go，用相同测试和压测对比价值。

## 5. 组件引入条件

- **MySQL**：需要事务、唯一约束和持久化时引入；验证并发报名、重复请求、索引和慢查询。
- **Redis**：需要缓存热点数据或限流计数时引入；验证命中率、过期、不可用和降级。
- **Prometheus/Grafana**：稳定请求路径后引入；验证请求量、错误率、延迟、依赖指标和告警。
- **Loki**：JSON 日志不足以支持故障关联时引入。
- **Kubernetes**：Compose 发布和回滚稳定后引入。
- **Agent**：指标、日志、发布记录和 Runbook 已存在后引入。
- **自动化巡检**：M2 引入只读规则检查；先输出结构化结果，再接入告警和 Agent。

## 6. 暂不选择

- Go 全量开发：避免语言学习阻塞系统设计，后续做有测试对比的局部迁移。
- 消息队列：第一版没有明确异步场景，避免无效复杂度。
- Elasticsearch：第一阶段 JSON 日志足够，后续按排障需求引入 Loki。
- 多云和多集群：先掌握单环境网络、资源、发布、监控和恢复。

## 7. 本地协作

- `main`：可运行基线；
- `feat/*`：功能开发；
- `experiment/*`：可回收实验；
- 每个里程碑至少一个可运行提交；
- GitHub 恢复后再添加远程仓库，不改变本地历史。

## 8. 每个组件的验收问题

1. 它解决了哪个具体问题？
2. 不使用它会有什么可观察后果？
3. 如何测试它正常工作和发生故障？
4. 它增加了哪些运维成本？
5. 能否用项目真实证据解释它？
