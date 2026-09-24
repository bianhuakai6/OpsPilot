# FastAPI 基础与本项目实践

## 1. FastAPI 在项目中的定位

FastAPI 是 Python Web 框架，适合构建 HTTP API 和后端服务。它负责接收请求、匹配路由、校验输入、调用业务函数、序列化响应，并根据代码自动生成 OpenAPI 文档。

它不是数据库、前端或完整的运维平台。在 OpsPilot 中，FastAPI 是平台的 API 层，后续控制台、自动巡检和 Agent 都通过 API 与平台交互。

当前请求链路：

```text
浏览器或客户端
  -> Uvicorn 接收 HTTP
  -> FastAPI 匹配路由
  -> Pydantic 校验输入
  -> 路由函数执行规则
  -> 存储层读取或更新状态
  -> FastAPI 返回 JSON
```

## 2. 应用入口

代码位置：`app/main.py`

```python
app = FastAPI(title="OpsPilot", version="0.1.0")
app.include_router(health_router)
app.include_router(activities_router)
```

`FastAPI(...)` 创建应用对象；`include_router` 把不同模块的接口挂载到同一个应用。入口只负责组装，不负责写预约规则，这样以后替换数据库或增加巡检模块时，边界更清晰。

启动命令：

```text
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`app.main` 表示模块，后面的 `app` 表示模块中的 FastAPI 对象。Uvicorn 是 ASGI 服务器，负责监听端口和处理网络连接；FastAPI 是应用框架，负责请求处理。

## 3. 路由与 HTTP 方法

代码位置：`app/routes/health.py`、`app/routes/activities.py`

```python
@router.get("/{activity_id}")
def get_activity_detail(activity_id: str):
    ...
```

装饰器把 HTTP 方法和 URL 绑定到 Python 函数。当前接口包括：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/healthz` | 检查进程是否能响应 |
| GET | `/api/v1/activities/{activity_id}` | 查询活动状态和容量 |
| POST | `/api/v1/activities/{activity_id}/reservations` | 创建预约并改变状态 |

GET 通常用于读取资源，POST 通常用于创建或执行会改变状态的操作。`/api/v1` 是 API 版本前缀，后续可以并行维护不同版本。

## 4. 参数来源与 Pydantic 校验

FastAPI 会根据函数签名判断参数来自哪里：

```python
def reserve(
    activity_id: str,                 # 路径参数
    request: ReservationRequest,      # JSON 请求体
    idempotency_key: str = Header(...),# 请求头
):
    ...
```

请求体模型位于 `app/models.py`：

```python
class ReservationRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
```

当 `user_id` 缺失、为空或过长时，FastAPI 会返回 `422`，业务函数不会执行。输入格式错误和业务冲突要区分：参数校验失败通常是 `422`，名额耗尽或重复预约属于业务冲突，当前返回 `409`。

## 5. 响应和异常

路由函数返回 Python 字典时，FastAPI 会把它序列化为 JSON。预约成功显式设置状态码 `201`，表示创建了新的预约。

业务错误使用 `HTTPException`：

```python
raise HTTPException(
    status_code=409,
    detail={"code": "capacity_exhausted", "message": "活动名额已满"},
)
```

`code` 是稳定的机器可读错误码，`message` 方便人阅读。前端和自动化工具应优先依赖 `code`，不要依赖可能变化的中文描述。

## 6. 自动生成的 `/docs`

FastAPI 根据路由装饰器、函数签名和 Pydantic 模型生成 OpenAPI 描述，并提供 `/docs` Swagger UI 页面。该页面适合：

- 查看接口清单；
- 查看参数和请求体结构；
- 使用 `Try it out` 手工发请求；
- 快速确认状态码和响应格式。

`/docs` 是 API 调试界面，不是最终运维控制台。后续控制台会调用这些 API，展示服务状态、巡检结果、指标和 Agent 建议。

## 7. FastAPI 常见能力

### 依赖注入

`Depends` 可以统一提供数据库连接、当前用户、权限校验等依赖。当前原型还没有接入认证和数据库，后续会在配置与持久化阶段使用。

### 异步处理

`async def` 适合包含异步 I/O 的接口，例如异步访问数据库或外部 API。异步并不自动解决并发一致性问题；名额扣减仍需要数据库事务或其他并发控制。

### 中间件

中间件可以统一处理请求日志、耗时、追踪 ID、跨域和异常边界。后续结构化日志和指标会优先放在这一层或统一依赖中。

### OpenAPI 与类型注解

Python 类型注解同时服务于参数校验、编辑器提示和接口文档。类型写得准确，运行时行为和文档才更可靠。

## 8. 当前实现的边界

当前 `app/store.py` 使用进程内字典和 `Lock`：

- 服务重启会丢失数据；
- 多进程或多副本不共享状态；
- `Lock` 只能保护同一进程内的线程；
- 尚未接入认证、数据库事务、日志、指标和权限审计。

因此当前版本适合本地学习和验证 API 行为，不应描述为生产级平台。后续用 MySQL、Redis、结构化日志和巡检模块逐项替换这些临时能力。

## 9. 在 OpsPilot 中的目标流程

```text
运维控制台
  -> FastAPI 控制面 API
  -> 权限和参数校验
  -> 服务层
  -> MySQL / Redis / 指标和日志系统
  -> 巡检、发布、回滚或 Agent 分析
  -> 返回结果并记录审计
```

Agent 不应绕过 API 直接修改数据。更可靠的流程是 Agent 提供证据和建议，人工审批后由受控 API 执行，并记录操作审计。

## 10. 面试表达练习

> 我使用 FastAPI 构建平台控制面 API，通过路由定义资源查询、预约和健康检查接口，使用 Pydantic 做输入校验，使用幂等键处理网络重试，并用并发测试验证单进程内不会超卖。当前状态存储仍是内存原型，后续会用数据库事务、唯一约束和可观测性组件替换临时实现。

## 11. 自测问题

1. Uvicorn 和 FastAPI 分别负责什么？
2. 为什么缺少 `user_id` 是 `422`，名额耗尽是 `409`？
3. `activity_id`、`user_id` 和 `Idempotency-Key` 分别来自请求的哪里？
4. 为什么 `/docs` 不是运维控制台？
5. 为什么单进程 `Lock` 不能解决多副本部署的一致性问题？
