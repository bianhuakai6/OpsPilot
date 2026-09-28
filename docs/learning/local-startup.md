# 本地一键启动说明

## 使用方式

### 推荐：仅依赖 Git 和 Docker Desktop 的容器化方式

在 Windows 上克隆仓库并启动 Docker Desktop 后，双击项目根目录的 `start-container.bat`。该入口会在 Docker 测试镜像中执行 `pytest`，测试通过后构建带 Git SHA 的 API 镜像，启动 MySQL、Redis 和 API 容器，并等待 `/readyz` 就绪。此流程不要求宿主机安装 Python、pytest 或项目依赖。

首次运行需要下载 Python 基础镜像和依赖，耗时取决于网络；Docker 会缓存构建层，后续启动会快很多。该入口适用于 Windows + Docker Desktop，API 和依赖都运行在容器中。

也可以在 PowerShell 中执行：

```powershell
.\scripts\container-start.ps1
```

### 原生开发模式

在 Windows 资源管理器中双击项目根目录的 `start-project.bat`。此模式要求本机安装 Python 3.13 和项目依赖；它会用 Docker 启动 MySQL、Redis，再由本机 Python/Uvicorn 运行 API。随后显示验收地址：

- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/healthz`
- 就绪检查：`http://127.0.0.1:8000/readyz`（应显示 MySQL、Redis 均为 `connected`）

保持启动窗口打开即可使用服务；按 `Ctrl+C` 可以停止服务。

也可以在 PowerShell 中直接运行主脚本，并指定端口：

```powershell
.\scripts\start.ps1 -Port 8001
```

默认 `-Mode full` 会在依赖不可用时明确失败，不会悄悄退回内存模式。仅在有意进行无数据库的轻量开发时显式运行：

```powershell
.\scripts\start.ps1 -Mode memory
```

完整模式会明确设置 `OPSPILOT_STORAGE=mysql`、`OPSPILOT_REDIS_ENABLED=true`。配置可以通过 `OPSPILOT_HOST`、`OPSPILOT_PORT` 覆盖；脚本的 `-Port` 参数优先级更高。

如果 8000 已有旧版 OpsPilot 正在运行，脚本不会替你终止它，也不会假装切换了运行模式，而会检查 `/readyz` 并提示不匹配。请回到旧服务启动窗口按 `Ctrl+C` 停止，再重新双击 `start-project.bat`。该脚本只负责启动容器，不会自动停止容器。

## 脚本做了什么

1. 自动切换到项目根目录，避免从其他目录双击时找不到 `app` 包。
2. 优先使用 `.venv\Scripts\python.exe`，没有虚拟环境时使用系统 `python`。
3. 完整模式下检查 Docker Engine、启动 Compose 依赖并等待健康状态。
4. 检查端口是否已被占用；已有 OpsPilot 实例会核对就绪依赖状态，冲突进程不会被终止。
5. 按选择的模式显式设置依赖配置并启动 `app.main:app`。

If the selected port already serves this OpsPilot instance, the script reuses it and prints its URLs. If another process owns the port, the script reports that process and exits without terminating it.

## 阶段性维护规则

每当服务启动方式、Python 版本、端口约定或依赖安装方式发生变化，必须同步检查：

- `scripts/start.ps1`
- `start-project.bat`
- 本文档
- README 中的运行说明

每个阶段完成时，都要至少验证一次“依赖健康 -> `/readyz` 显示 MySQL/Redis connected -> `/healthz` -> `/docs` -> 停止 API”；依赖容器由用户显式 `docker compose down` 停止。脚本不安装 Python 包、不删除数据卷，也不终止来源不明的进程。
