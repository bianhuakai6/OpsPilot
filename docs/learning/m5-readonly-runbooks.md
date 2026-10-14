# M5：只读 Runbook 推荐

## 这块解决什么问题

巡检能够报告“Redis 连接失败”，但只看告警名称还不够，操作者还需要知道先查什么、正常结果应该是什么，以及哪些动作不能贸然执行。本阶段把两类依赖故障的排查顺序整理成结构化 Runbook，并在告警旁展示。

## 请求链路

1. `POST /api/v1/inspections/run` 执行只读巡检。
2. 失败检查由 `InspectionAlertStore` 关联为带 `alert_id` 的告警事件。
3. 控制台读取 `GET /api/v1/alerts`，再按告警 ID 请求 `GET /api/v1/alerts/{alert_id}/runbook`。
4. 服务端读取告警的 `check_id`，只做精确匹配，例如 `redis_connectivity` 对应 `redis-connectivity`。
5. 页面展示核查步骤和预期结果；恢复动作仍由操作者判断和执行。

独立查询入口为 `GET /api/v1/runbooks` 和 `GET /api/v1/runbooks/{runbook_id}`。当前有 Redis、MySQL 两份 Runbook；其它检查项没有匹配时会明确显示“暂无匹配的 Runbook”，不影响告警和巡检结果。

供后续 Agent 或人工排障使用的聚合入口是 `GET /api/v1/ops-context/alerts/{alert_id}`。它把告警事实、Runbook、当前 SLO 快照和来源巡检 ID 放在同一个结构中，并返回 `agent_boundary` 声明只读、未执行命令、未调用外部模型且操作需要人工审批。

## Runbook 字段怎么看

- `symptoms`：可能观察到的现象。
- `safe_checks`：只读核查步骤；`kind=command` 是终端命令，`kind=browser` 是浏览器地址，`expected` 描述预期结果。
- `hypotheses`：需要证据验证的可能原因，不是系统确认的根因。
- `manual_actions`：供人判断的恢复建议。
- `forbidden_actions`：明确禁止的高风险操作，例如清空 Redis 或删除数据库卷。
- `requires_human_approval`：说明建议不代表授权执行。

接口返回的 `execution.executed=false` 是重要边界：平台目前只提供文档化建议，没有 Shell 工具、外部模型调用或自动修复执行器。不要把 Runbook 推荐描述成已经完成的 AI 根因分析或自治运维。

## 当前边界

告警状态存于 API 单进程内存，服务重启后会清空；多副本也不会共享。Runbook 是代码中的静态结构化数据，匹配依赖稳定的 `check_id`。当前只覆盖 Redis/MySQL 连接异常。后续 Agent 需要再接入经过筛选的日志、指标和发布记录上下文，生成可验证的根因候选，并以评估样例、人工审批和操作审计约束风险。

上下文接口当前不会查询完整日志、发布历史或数据库连接配置；这是刻意的最小权限边界，避免 Agent 一开始就获得过宽的数据访问范围。

## 受限只读工具

第三块 M5 能力提供 `GET /api/v1/agent/tools` 工具目录，以及固定工具调用入口 `GET /api/v1/agent/tools/{tool_name}`。目前白名单只有 `list_alerts`、`latest_inspections`、`slo_snapshot` 和 `release_history`，并把 `limit` 限制在 1 到 20。工具调用不会执行 Shell、访问任意 URL 或修改服务状态；发布记录只返回时间、动作、版本、镜像、Git SHA、阶段和就绪状态等安全元数据。发布记录是宿主机本地文件，未挂载到 API 容器时返回 `available=false` 和原因，不把“不可见”伪装成“没有记录”。

工具目录就是后续模型适配层的契约：模型只能从目录中选择工具，应用服务负责校验工具名和参数，再返回结构化 JSON。模型不能自行拼接命令绕过白名单。

## 模型适配层（第一版）

当前已接入 Responses 原生协议客户端。模型配置来自 `.env` 或容器环境变量：`OPSPILOT_MODEL_BASE_URL`、`OPSPILOT_MODEL_RESPONSES_PATH`、`OPSPILOT_MODEL`、`OPSPILOT_MODEL_API_KEY` 和超时配置。默认值对应 AirCode 的 `https://api.aircode.xin/responses` 与 `gpt-5.6-terra`；路径可配置为 `/v1/responses`，便于兼容不同网关。

分析入口是 `POST /api/v1/agent/analyze/{alert_id}`。服务端把告警、匹配 Runbook 和 SLO 快照组织成提示词，要求模型返回根因候选、证据、核查步骤、风险等级和人工审批字段。接口只返回模型文本和响应 ID，不执行文本中的命令。没有 API Key、网络失败或响应格式不符合 Responses 结构时，接口返回明确的 `model_unavailable`，而不是让应用启动失败。

API Key 只放在本机 `.env`，该文件已被 Git 忽略；`.env.example` 只包含空占位符。不要把 Key 放进代码、镜像、提交或聊天内容。模型请求设置 `store=false`，并且当前服务不持久化模型原文，后续还需要增加脱敏、响应结构校验和分析审计。

2026-10-14 已完成一次真实本机闭环：停止 Redis 产生 open 告警，调用 `/api/v1/agent/analyze/{alert_id}` 返回 HTTP 200、模型为 `gpt-5.6-terra` 且有文本结果；随后恢复 Redis，巡检 pass、`/readyz` ready、原告警 resolved。该证据证明连接和协议可用，不代表模型结论天然正确；当前分析结果仍需人工阅读，不能自动执行。

模型输出现在必须是 JSON 对象，并包含 `root_cause_candidates`、`evidence`、`recommended_checks`、`risk_level`、`requires_human_approval` 五个字段，且审批字段必须为 `true`。不符合契约时返回 `invalid_model_output`，不会把自由文本直接当成可信结论。

## 如何验证

- 自动测试：`python -m pytest -q`，覆盖字段边界、精确匹配、无匹配响应和“永不执行”声明。
- 浏览器：打开 `/dashboard`，有 Redis/MySQL 告警时查看建议步骤；其它告警仍应显示，但显示无匹配提示。
- 故障演练：停止 Redis 后运行一次巡检，确认产生 open 告警并能看到 Redis Runbook；启动 Redis 后再次巡检，确认原告警 resolved。

## 面试时怎么解释

“我先把 Runbook 做成只读、结构化的运维知识层。巡检告警通过稳定的检查项 ID 精确映射排查步骤，页面展示命令和预期证据，但不直接执行修复。这样可以先验证上下文组织和人工审批边界，再逐步接入 Agent 分析，同时避免把一个未经验证的模型输出变成生产动作。”
