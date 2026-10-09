# OpsPilot Agent 交接说明

> 记录日期：2026-10-09。本文中的 Git 同步状态可能随后变化；接手前请以 `git status -sb` 和 `git log` 实际检查为准。

## 项目目标与协作方式

OpsPilot 是一个面向 SRE / 平台运维 / 云计算学习与演示的本地项目。在线资源预约只是承载业务流量的示例，重点是围绕它实践发布、可观测性、巡检、故障处理、恢复和 Agent 辅助运维。

协作时请遵循：

- 用户希望理解项目，不要只交付代码。每个有实质内容的阶段，要说明改动解决什么问题、关键原理、如何验证，以及仍有哪些边界；合适时补充中文学习文档。
- 代码模块或独立功能块加简短中文分区注释，解释意图即可，避免逐行注释。
- 不虚构完成情况。区分自动化测试、实际本机验证和设计设想，并给出可复核证据。
- 变更前检查 `git status`，保留用户已有改动。阶段性变更按仓库约定用中文提交；不要未经用户指示推送远端。
- Docker 镜像清理要谨慎。正式 `opspilot:<版本>-<Git短SHA>` 镜像是发布/回滚证据，不可当临时镜像清掉；清理脚本默认预览，只有确认目标为临时验证镜像后才考虑 `-Apply`。

## 当前仓库状态

- 仓库：`https://github.com/bianhuakai6/OpsPilot.git`
- 分支：`main`
- 接手时请检查本地 `main` 是否领先 `origin/main`；未推送的提交不会自动出现在另一台设备。
- 开始操作前检查工作区，保留任何已有改动。
- 最近一组工作：容器化一键启动、容器内测试、临时测试镜像清理保护、压力测试时长/日志开销修正，以及本机 JSONL 发布记录。

## 当前可运行内容

### 推荐：纯 Docker 启动

新电脑只需要 Git、Docker Desktop（Docker Engine 已启动）即可运行，不要求宿主机安装 Python。

1. 在当前设备先推送 `main` 上尚未推送的提交。
2. 另一台设备克隆或拉取仓库最新 `main`。
3. 启动 Docker Desktop，等待 Engine 就绪。
4. 双击仓库根目录的 `start-container.bat`。
5. 浏览器打开 `http://127.0.0.1:8000/dashboard`；压力测试页面为 `/load-test`。

`start-container.bat` 调用 `scripts/container-start.ps1`，由 Docker 完成测试镜像构建和 pytest、正式应用镜像构建，再启动 API、MySQL、Redis。测试失败时不应继续部署。应用就绪检查会验证 API 和 MySQL/Redis 连接。

常用状态与停止操作：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\release-local.ps1 -Action status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\release-local.ps1 -Action stop
```

`stop` 当前只停止 API 容器，MySQL/Redis 和持久化卷保留。需要彻底停止 Compose 服务时，先确认没有其他任务依赖该本地环境，再执行：

```powershell
docker compose -f docker-compose.yml -f docker-compose.release.yml down
```

不要加 `-v`，否则会删除本地数据库持久化卷。

### 本机 Python 开发启动

`start-project.bat` 是原生 Python 开发模式，适合改代码/调试，需要宿主机 Python。它与 Docker API 都使用 8000 端口，不能同时运行。另一台电脑装有 Python 不会影响 Docker 模式，也不要求为了 `start-container.bat` 配置 Python。

## 交接时的运行与验证证据

交接检查时本机 Docker Compose 状态：

| 服务 | 容器 | 镜像 | 状态 | 主机端口 |
| --- | --- | --- | --- | --- |
| API | `opspilot-api` | `opspilot:0.1.0-fd7dd96` | healthy | 8000 |
| MySQL | `opspilot-mysql` | `mysql:8.4` | healthy | 3306 |
| Redis | `opspilot-redis` | `redis:7.4` | healthy | 6379 |

最近一次完整容器启动验收记录：Docker 内测试 `39 passed, 4 skipped`；API readiness 显示 ready，MySQL/Redis 为 connected。当前页面在 `http://127.0.0.1:8000/dashboard`。这证明当前设备上的该版本能启动，不等同于已在另一台机器验收；新机器仍要实际双击启动并复核页面和容器状态。

仓库中还留有若干带正式 Git SHA 的历史镜像，作为构建/回滚记录保留是有意行为，不代表它们正在运行。当前运行 API 使用 `0.1.0-fd7dd96`。临时测试镜像应按 `scripts/cleanup-images.ps1` 的预览结果逐一判断，不能批量删除正式标签。

## 当前实现范围与下一阶段

README 将项目标为 M3（发布与回滚闭环）进行中。M1 业务闭环和 M2 本地依赖、可观测性、自动巡检、控制台、压力测试已有实现和学习记录；M3 已具备可追溯镜像构建、本地容器化部署入口和本机 JSONL 发布记录。M3 后续仍需补齐并验收：

1. 健康检查失败处理：验证发布未就绪时能清楚报告、保留诊断证据，并有明确的恢复路径。
2. 回滚演练：用上一个已验证镜像恢复，验证应用健康，并留下演练记录。

发布记录保存在被 Git 忽略的 `data/release-history.jsonl`，记录时间、版本、Git SHA、镜像、结果、失败阶段和就绪状态，不保存异常原文。它是本机数据，不随仓库跨设备同步。2026-10-09 验证过端口占用时的安全拒绝路径：记录结果为 `failed/port_check`，原有 API 仍 ready；完整成功发布路径还需后续在受控发布验证中确认。

然后再按 `DEVELOPMENT_PLAN.md` 评估 M4 故障演练与 SLO。不要跳过本地发布/回滚闭环，提前扩展云或 Kubernetes 范围。

## 新 Agent 接手流程

1. 先读本文、`README.md`、`DEVELOPMENT_PLAN.md`、`AGENT_WORKFLOW.md` 和相关 `docs/learning/` 学习记录。
2. 检查 `git status -sb`、最近提交和 Docker Compose 状态；不要假设交接时这台机器的服务仍在运行。
3. 若 `main` 领先远端且用户希望跨设备同步，提醒用户推送；不要私自改远端或重写历史。
4. 从 M3 剩余事项中选一个边界清楚的小阶段，先说明范围，再实现、测试、复核文档和 Git 差异。
5. 结束时说明页面/命令如何验收、测试结果、当前容器/镜像影响，以及建议的下一步。

## 重要配置与安全边界

- 默认本地端口：API `8000`、MySQL `3306`、Redis `6379`。启动前注意端口占用及 native/Docker API 冲突。
- Compose 中数据库凭据是本地演示默认值，不是生产安全配置；不要将其描述成适合公网部署的凭据。
- 当前项目仍是本地单机演示环境，尚未部署到云，也未实现 Kubernetes、生产级告警或自主 Agent 执行运维操作。
- 不在文档或提交中写入个人凭据、访问令牌、代理认证信息或机器专属路径。
