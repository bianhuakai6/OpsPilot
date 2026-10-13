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

## 如何验证

- 自动测试：`python -m pytest -q`，覆盖字段边界、精确匹配、无匹配响应和“永不执行”声明。
- 浏览器：打开 `/dashboard`，有 Redis/MySQL 告警时查看建议步骤；其它告警仍应显示，但显示无匹配提示。
- 故障演练：停止 Redis 后运行一次巡检，确认产生 open 告警并能看到 Redis Runbook；启动 Redis 后再次巡检，确认原告警 resolved。

## 面试时怎么解释

“我先把 Runbook 做成只读、结构化的运维知识层。巡检告警通过稳定的检查项 ID 精确映射排查步骤，页面展示命令和预期证据，但不直接执行修复。这样可以先验证上下文组织和人工审批边界，再逐步接入 Agent 分析，同时避免把一个未经验证的模型输出变成生产动作。”
