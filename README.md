# OpsPilot

本地启动：双击 `start-project.bat`，或在 PowerShell 中运行 `.\scripts\start.ps1`。启动后访问 `http://127.0.0.1:8000/docs`；脚本细节见 [本地启动说明](docs/learning/local-startup.md)。

MySQL 基础设施：Docker Engine 可用后运行 `powershell -File .\scripts\mysql.ps1 -Action up`，查看状态运行 `-Action status`。

面向在线服务的云原生应用交付与智能运维平台。

## 项目目标

以“在线资源预约服务”为示例负载，验证以下完整链路：

```text
开发 -> 构建 -> 发布 -> 观测 -> 告警 -> 故障分析 -> 受控恢复 -> 复盘
```

业务服务只是被运维对象，项目主体是发布、可观测性、可靠性和 Agent 辅助运维能力。

## 当前阶段

**M1：在线资源预约服务（进行中）**

已完成项目章程、开发规范、最小健康检查服务和 M1 内存版预约接口；自动化巡检已纳入 M2。当前 M1 接口测试已通过，下一步是补充 M1 验收记录后进入持久化设计。

## 文档入口

- [项目章程](PROJECT_CHARTER.md)：目标、边界和验收原则
- [开发计划](DEVELOPMENT_PLAN.md)：里程碑、产出和验收标准
- [Agent 协作规范](AGENT_WORKFLOW.md)：任务拆解、实现、验证和学习记录
- [Agent 使用手册](AGENT_PLAYBOOK.md)：从提需求升级为调查、编排、验证和复盘
- [版本控制规范](VERSION_CONTROL.md)：Git、GitHub、分支、提交和变更审查
- [业务场景](docs/01-business-scenario.md)：在线资源预约作为示例负载
- [接口与数据模型](docs/02-api-and-data-model.md)：请求契约、错误分类和数据库约束草案
- [M1 学习记录](docs/learning/m1-in-memory-service.md)：内存实现、幂等和并发边界
- [HTTP 接口与请求链路](docs/learning/http-api-and-request-flow.md)：理解 `/docs`、请求组成和服务调用路径
- [岗位技术分析](三类技术岗位共通技术点分析.md)：目标岗位和能力背景

## 开发原则

1. 先完成本地闭环，再迁移 Kubernetes 和云环境。
2. 每个功能必须有实现、验证、知识说明和结果记录。
3. 所有性能和可靠性指标必须通过实验获得。
4. Agent 提高效率，但设计、验证和最终决策由人负责。
5. 新需求必须说明收益、复杂度和对当前计划的影响。

## 下一步

完成 M1 人工学习验收后，进入 M2 数据库持久化和本地可观测性。环境基线见 [learning-baseline.md](learning-baseline.md)。
