# 本地一键启动说明

## 使用方式

在 Windows 资源管理器中双击项目根目录的 `start-project.bat`。脚本会启动本地 FastAPI 服务，并显示两个验收地址：

- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/healthz`

保持启动窗口打开即可使用服务；按 `Ctrl+C` 可以停止服务。

也可以在 PowerShell 中直接运行主脚本，并指定端口：

```powershell
.\scripts\start.ps1 -Port 8001
```

## 脚本做了什么

1. 自动切换到项目根目录，避免从其他目录双击时找不到 `app` 包。
2. 优先使用 `.venv\Scripts\python.exe`，没有虚拟环境时使用系统 `python`。
3. 启动前检查 FastAPI 和 Uvicorn 是否可导入。
4. 检查端口是否已被占用，并给出明确提示。
5. 启动 `app.main:app`，不绕过项目入口。

## 阶段性维护规则

每当服务启动方式、Python 版本、端口约定或依赖安装方式发生变化，必须同步检查：

- `scripts/start.ps1`
- `start-project.bat`
- 本文档
- README 中的运行说明

每个阶段完成时，都要至少验证一次“脚本启动 -> `/healthz` -> `/docs` -> 停止服务”，并在 Git 提交中记录启动方式是否变化。脚本只负责启动本地服务，不负责偷偷安装依赖或修改用户环境。
