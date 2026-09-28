# M3：本地容器化发布

## 1. 这一段解决什么问题

M2 的默认运行方式是：Python/Uvicorn 在宿主机运行，MySQL 和 Redis 由 Docker 提供。
这种方式适合开发，但和正式交付还有差距：应用进程依赖本机 Python 环境，换一台机器需要重新配置。

M3 增加了一个可追溯的 API 镜像和本地发布入口：

```text
代码 + 测试 -> build-image.ps1 -> opspilot:版本-Git短SHA
                                      |
                                      v
                         release-local.ps1 -> opspilot-api
```

镜像标签里的 Git 短 SHA 用来回答“现在运行的到底是哪次代码提交”。

## 2. 构建和部署为什么分开

`scripts/build-image.ps1` 负责两件事：先运行测试，再构建镜像并写入 OCI 元数据。
`scripts/release-local.ps1` 只负责部署已经存在的当前提交镜像，并等待服务就绪。

这对应 CI/CD 的基本边界：

- CI（持续集成）：检查代码、运行测试、生成不可变交付物。
- CD（持续交付/部署）：选择一个已经生成的交付物，启动它并验证结果。

如果镜像不存在，发布脚本会拒绝部署，不会偷偷拉取远程镜像，也不会把“构建失败”伪装成“发布成功”。

## 3. Compose 如何组成一次发布

发布使用两个 Compose 文件：

- `docker-compose.yml`：MySQL、Redis 等本地基础设施。
- `docker-compose.release.yml`：API 容器、端口映射、环境变量、依赖和健康检查。

命令中的两个 `-f` 会把后一个文件作为覆盖层合并到前一个文件。API 容器映射为 `opspilot-api`，宿主机端口 `8000` 映射到容器端口 `8000`。

## 4. 容器里为什么不能写 127.0.0.1

在 API 容器内，`127.0.0.1` 指的是 API 容器自己，不是 MySQL 或 Redis。
Compose 会为服务建立内部网络，并提供服务名解析，因此 API 使用：

```text
mysql:3306
redis:6379
```

宿主机浏览器仍然访问 `http://127.0.0.1:8000`，请求经过端口映射进入 API 容器；API 再通过 Compose 内部网络访问 MySQL 和 Redis。

## 5. 健康检查和就绪检查

容器 healthcheck 请求容器内部的 `/readyz`。这个接口不仅检查 API 进程，还检查 MySQL 和 Redis 的连接状态。

发布脚本等待两个条件同时成立：

1. Docker 报告 API 容器为 `healthy`。
2. 宿主机请求 `/readyz` 返回 `ready`，且 MySQL、Redis 都是 `connected`。

所以“容器启动了”不等于“服务可以接流量”。只有依赖也准备好，发布才会报告成功。

## 6. 停止边界

`release-local.ps1 -Action stop` 只停止 `opspilot-api`，不会删除 MySQL、Redis，也不会删除数据卷。
这样可以释放默认端口 `8000`，同时保留基础设施供下一次发布复用。

脚本还会在部署前检查 `8000` 是否已被占用，避免误覆盖正在运行的 native API。

## 7. 本次真实验收

本阶段已验证：

- API 镜像 `opspilot:0.1.0-9bbfba2` 已存在并成功运行。
- API、MySQL、Redis 容器均为 running，健康状态为 healthy。
- `/readyz` 返回 `ready`，MySQL 和 Redis 均为 `connected`。
- 停止演练只停止 API，端口释放，MySQL/Redis 保持运行。
- 再次 deploy 可以恢复 API，默认访问地址仍是 `http://127.0.0.1:8000`。
- 自动化测试通过：`38 passed, 4 skipped`（MySQL 集成测试按环境开关执行）。

## 8. 当前还没有做什么

当前是本地容器化发布，不等于完整生产发布系统。还没有远程 CI Runner、发布记录持久化、自动回滚、灰度发布和 Kubernetes 部署。这些属于后续 M3/M4/M6 的范围，不能在当前阶段虚构为已完成能力。
