# OpsPilot

本地启动：双击 `start-project.bat`，或在 PowerShell 中运行 `.\scripts\start.ps1`。启动后访问 `http://127.0.0.1:8000/docs`；脚本细节见 [本地启动说明](docs/learning/local-startup.md)。
运维控制台：访问 `http://127.0.0.1:8000/dashboard`，页面会读取健康检查、依赖状态、活动容量和自动巡检结果。

MySQL 基础设施：Docker Engine 可用后运行 `powershell -File .\scripts\mysql.ps1 -Action up`，查看状态运行 `-Action status`。

数据库模式和启动方式见 [MySQL 本地基础设施](docs/learning/mysql-local-infrastructure.md)；默认启动脚本使用 MySQL + Redis 完整模式，自动化测试仍可在隔离环境使用内存模式。

面向在线服务的云原生应用交付与智能运维平台。

## 项目目标

以“在线资源预约服务”为示例负载，验证以下完整链路：

```text
开发 -> 构建 -> 发布 -> 观测 -> 告警 -> 故障分析 -> 受控恢复 -> 复盘
```

业务服务只是被运维对象，项目主体是发布、可观测性、可靠性和 Agent 辅助运维能力。

## 当前阶段

**M3：发布与回滚闭环（进行中）**

M2 已完成本地依赖、可观测性、巡检、控制台和压力测试闭环。M3 当前从可追溯镜像构建开始：每个构建产物绑定项目版本和 Git 提交；后续将补充容器化启动、发布记录、健康失败处理和回滚演练。

## 文档入口

- [项目章程](PROJECT_CHARTER.md)：目标、边界和验收原则
- [开发计划](DEVELOPMENT_PLAN.md)：里程碑、产出和验收标准
- [Agent 协作规范](AGENT_WORKFLOW.md)：任务拆解、实现、验证和学习记录
- [Agent 使用手册](AGENT_PLAYBOOK.md)：从提需求升级为调查、编排、验证和复盘
- [版本控制规范](VERSION_CONTROL.md)：Git、GitHub、分支、提交和变更审查
- [业务场景](docs/01-business-scenario.md)：在线资源预约作为示例负载
- [接口与数据模型](docs/02-api-and-data-model.md)：请求契约、错误分类和数据库约束草案
- [M1 学习记录](docs/learning/m1-in-memory-service.md)：内存实现、幂等和并发边界
- [M2 压测基线](docs/learning/m2-load-test.md)：本地只读 HTTP 压测及结果解读
- [M2 验收记录](docs/learning/m2-acceptance.md)：当前本地依赖和可观测性闭环证据
- [M2 可视化压力测试](docs/learning/m2-visual-load-testing.md)：任务 API、参数上限和页面交互
- [M3 镜像构建](docs/learning/m3-image-build.md)：镜像、标签、构建提交与当前边界
- [HTTP 接口与请求链路](docs/learning/http-api-and-request-flow.md)：理解 `/docs`、请求组成和服务调用路径
- [岗位技术分析](三类技术岗位共通技术点分析.md)：目标岗位和能力背景

## 开发原则

1. 先完成本地闭环，再迁移 Kubernetes 和云环境。
2. 每个功能必须有实现、验证、知识说明和结果记录。
3. 所有性能和可靠性指标必须通过实验获得。
4. Agent 提高效率，但设计、验证和最终决策由人负责。
5. 新需求必须说明收益、复杂度和对当前计划的影响。

## 下一步

下一步完成可追溯镜像构建，再推进容器化启动、发布记录和回滚闭环。环境基线见 [learning-baseline.md](learning-baseline.md)。
