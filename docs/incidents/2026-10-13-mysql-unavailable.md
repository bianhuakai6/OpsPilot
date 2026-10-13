# MySQL 不可用演练复盘

## 基本信息

- 演练时间：2026-10-13 15:40（Asia/Shanghai）
- 故障对象：本地 Compose 服务 `opspilot-mysql`
- 演练环境：Windows 宿主机 + Docker Desktop，本地 OpsPilot 容器
- 影响范围：就绪探针和只读巡检；未发送预约写请求，Redis 与数据卷未修改

## 目标与注入

- 验证目标：确认 MySQL 不可用时探针及时失败、巡检能识别数据库依赖，恢复后服务重新就绪。
- 故障注入：执行 `docker stop opspilot-mysql`，保持 API 和 Redis 运行。
- 预期信号：`/readyz` 返回 503，错误码 `database_unavailable`。

## 观测与恢复

- 故障窗口 `/readyz` 返回 HTTP 503，实测耗时约 4.1 秒。
- MySQL 启动后等待 Docker healthcheck 变为 healthy；`/readyz` 返回 ready 且 MySQL、Redis 均 connected。
- 恢复后的巡检整体 pass，`mysql_connectivity` 为 pass。
- 初次演练显示巡检在数据库连接异常时等待时间偏长，因此补充 SQLAlchemy `connect_timeout`、`read_timeout` 和 `write_timeout` 均为 2 秒；完整复测需在新镜像部署后进行。

## 改进项

- 已完成：将 MySQL 连接超时集中配置在 `app/database.py`，并用单元测试锁定配置。
- 待复测：部署含超时修复的新镜像后，停止 MySQL，确认巡检也能在有限窗口内返回 fail 报告。
- 尚未覆盖：MySQL 慢查询、连接池耗尽和事务锁等待演练。
