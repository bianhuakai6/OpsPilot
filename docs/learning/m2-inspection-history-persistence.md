# M2 巡检历史持久化

## 这阶段解决了什么

巡检会在 API 进程里读取应用、MySQL 和 Redis 的状态。此前结果只放在 Python 的 `deque` 中：服务一重启，历史就消失；如果启动多个 API 进程，每个进程看到的历史也不相同。

现在 MySQL 模式会将每次巡检拆成“报告概要”和“检查明细”保存。`inspection_runs` 一行代表一次巡检，`inspection_checks` 的多行代表这次巡检逐项检查的证据与建议。内存模式仍然保留，便于不启动数据库时运行项目。

## 请求和数据流

```text
POST /api/v1/inspections/run
  -> 执行只读检查
  -> MySQL 模式：写入 inspection_runs 和 inspection_checks
  -> 返回本次报告

GET /api/v1/inspections/history
  -> MySQL 模式：按 checked_at 倒序查询概要，再按巡检 ID 查询明细
  -> 内存模式：读取当前进程 deque
```

相关代码：

- `app/inspection.py`：检查依赖并生成报告；MySQL 模式调用保存层。
- `app/inspection_store.py`：建表、保存报告、读取历史的 SQL。
- `app/routes/inspections.py`：根据运行配置选择 MySQL 或内存历史。
- `app/runtime.py`：MySQL 模式启动时确保巡检表存在，兼容已经创建的数据卷。
- `infra/mysql/init/001_schema.sql`：全新 MySQL 数据卷的初始表结构。
- `tests/test_mysql_integration.py`：用真实 MySQL 验证保存、明细、排序和读取。

## 为什么拆成两张表

一次巡检通常含多个不同检查项。若将明细拼成一个大 JSON，能快速起步，但筛选单项异常、统计故障类型和给检查项加约束都会更麻烦。拆表后，报告与明细之间用 `inspection_id` 关联：一条报告对应多条明细。当前读取采用简单的逐条查询，历史条数上升后可以再改成批量查询，避免 N+1 查询。

## 如何理解“重启后还能查到”

MySQL 容器的数据卷保存数据库文件；API 进程重启不会删除数据库里的行。启动时应用只负责检查表是否存在，历史接口从 MySQL 重新读取。相反，内存模式的数据只存在于当前 Python 进程，进程退出后自然消失。

本地验收时应分别确认：API 返回巡检 ID；MySQL 有同 ID 的报告和明细；停止并重启 API 后，历史接口仍返回该 ID。不要仅凭页面显示就推断数据已持久化。

## 当前边界与后续改进

- 巡检是只读检测，不会自动重启服务、清理数据或修复依赖。
- 当前存储了检查结果，但尚未实现定时调度、告警通知、保留周期和历史分页。
- 多次检查明细目前逐个读取；数据量增大后应批量读取并增加适当索引。
- 集成测试只清理自己使用的固定测试 ID，不清理真实巡检记录。

## 复盘问题

1. 为什么进程内 `deque` 不能作为多副本服务共享的历史存储？
2. `inspection_runs` 和 `inspection_checks` 分别承担什么职责？
3. 数据库数据卷、数据库表、API 进程分别在哪个生命周期中存活？
4. 如果历史增长到数十万条，为什么需要分页和批量读取明细？
