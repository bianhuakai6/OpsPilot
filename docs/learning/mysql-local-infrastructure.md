# MySQL 本地基础设施

## 当前完成范围

本阶段加入 MySQL 8.4 的 Docker Compose 配置和初始化表结构，但应用预约接口仍使用内存存储。这里先验证数据库基础设施可启动、可健康检查，下一阶段再接入 SQLAlchemy 和真实事务。

## 启动与停止

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mysql.ps1 -Action up
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mysql.ps1 -Action status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mysql.ps1 -Action logs
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mysql.ps1 -Action down
```

首次启动会拉取 `mysql:8.4` 镜像，可能需要等待网络下载。数据保存在 Docker 命名卷 `opspilot-mysql-data`，普通 `docker compose down` 不会删除它。

## 数据库结构

初始化脚本位于 `infra/mysql/init/001_schema.sql`，创建：

- `activities`：活动、容量和已预约计数；
- `reservations`：成功预约，唯一约束防止同一用户重复预约；
- `idempotency_records`：幂等键、请求指纹和原始响应。

初始化脚本只在空数据卷第一次启动时执行。修改表结构后应使用迁移工具或明确重建测试卷，不能假设脚本会自动重新执行。

## 配置与安全边界

Compose 默认值仅用于本地学习，不可直接用于生产。可通过 `.env` 覆盖 `MYSQL_DATABASE`、`MYSQL_USER`、`MYSQL_PASSWORD` 和 `MYSQL_ROOT_PASSWORD`；`.env` 已被 Git 忽略，密码不能提交到仓库。

## 本阶段验收

验收包括：容器处于 `healthy`，3306 端口可连接，三张表存在，默认活动已初始化。应用接口仍以内存状态为准，直到 SQLAlchemy 存储层完成并通过重启、并发、幂等和回滚测试。
