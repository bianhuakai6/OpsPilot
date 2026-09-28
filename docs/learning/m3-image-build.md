# M3 可追溯镜像构建

## 解决的问题

本地直接运行 Python 时，代码来自哪个 Git 提交、运行依赖如何安装，并没有被封装成一个可交付对象。Docker 镜像把应用代码和运行依赖打包成不可变构建产物，后续发布时部署的是明确标签的镜像，而不是某台机器上的工作目录。

## 构建方式

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-image.ps1
```

脚本先执行默认 `pytest -q`。通过后从 `pyproject.toml` 读取版本号、从 Git 读取当前短提交号，并构建类似下面的镜像：

```text
opspilot:0.1.0-46c3dc6
```

也可以人为指定一个标签：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-image.ps1 -Tag candidate-001
```

镜像标签用于人阅读和部署引用；OCI 标签 `org.opencontainers.image.version`、`org.opencontainers.image.revision` 会记录项目版本和构建提交。可检查它们：

```powershell
docker image inspect opspilot:0.1.0-46c3dc6 --format '{{json .Config.Labels}}'
```

## 当前边界

此阶段只构建和验证镜像，不会自动运行容器、修改 8000 端口或取代现有本地启动方式。镜像默认使用内存存储；后续发布阶段会通过运行配置接入 MySQL、Redis，并加入部署后的 `/readyz` 验证和回滚。默认构建测试不启用会清理测试数据的 MySQL 集成用例；需要时应先检查本地数据，再显式设置 `OPSPILOT_RUN_MYSQL_TESTS=1`。
