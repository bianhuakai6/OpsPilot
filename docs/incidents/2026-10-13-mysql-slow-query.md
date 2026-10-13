# MySQL 慢查询采集演练复盘

## 基本信息

- 演练时间：2026-10-13 16:01（Asia/Shanghai）
- 对象：Compose 中的 MySQL 8.4
- 目标：验证 MySQL 慢日志能否捕获超过阈值的查询，不影响预约业务数据

## 注入与证据

- 演练前配置：`slow_query_log=OFF`、`long_query_time=10` 秒、`log_output=FILE`。
- 临时将日志输出切换为 `TABLE`、阈值设为 1 秒并打开慢日志，执行只读语句 `SELECT SLEEP(2)`。
- `mysql.slow_log` 捕获到该语句，`query_time=00:00:02.000590`，与预期延迟相符。
- 查询仅等待两秒，不访问或修改 OpsPilot 业务表。

## 恢复和结论

- 立即恢复原始全局设置：`slow_query_log=OFF`、`long_query_time=10`、`log_output=FILE`；复查结果与演练前一致。
- API、MySQL、Redis 均保持 healthy，`/readyz` 返回 ready。
- 此实验验证了 MySQL 原生慢查询日志的采集路径，不代表应用已经有慢查询告警、分析看板或自动优化能力。
- 后续改进：将采集的慢 SQL 与 API 延迟/Trace 关联，并建立阈值告警与复盘流程。
