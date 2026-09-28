# MySQL 本地基础设施

> Python 驱动说明：项目通过 PyMySQL 连接 MySQL 8.4。MySQL 8 默认使用 `caching_sha2_password` 认证，PyMySQL 在非 TLS 本地连接中完成完整认证时需要 `cryptography` 来加密认证数据，因此该库作为应用依赖固定安装。它不负责数据库连接池或 SQL 执行。

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

## 应用切换到 MySQL 模式

数据库容器健康后，默认启动脚本会自动选择 MySQL + Redis 完整模式并使用项目默认端口 8000。若当前 8000 仍运行旧配置实例，先在其启动窗口按 Ctrl+C 停止，再运行 `start-project.bat`。需要单独验证 MySQL 时仍可显式指定端口启动：

```powershell
$env:OPSPILOT_STORAGE = "mysql"
$env:OPSPILOT_PORT = "8003"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

然后访问 `http://127.0.0.1:8003/readyz`。此模式下活动查询、预约和幂等记录走 MySQL；未设置 `OPSPILOT_STORAGE` 时仍使用内存模式。

## 本阶段验收

验收包括：容器处于 `healthy`，3306 端口可连接，三张表存在，默认活动已初始化；MySQL 集成测试通过并验证并发不超卖、幂等重试和重复预约回滚。应用默认仍是内存模式，只有设置 `OPSPILOT_STORAGE=mysql` 才切换到数据库。
