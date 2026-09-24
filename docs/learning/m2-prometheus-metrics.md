# M2 Prometheus 指标

## 为什么需要指标

日志适合查看某一次请求的细节，指标适合观察一段时间的总体趋势。SRE 常用指标回答：请求是否变多、错误率是否上升、响应是否变慢。

本阶段提供 Prometheus 格式的 `/metrics`，记录：

- `opspilot_http_requests_total`：按方法、路径和状态码统计请求总数；
- `opspilot_http_request_duration_seconds`：按方法和路径统计响应耗时分布。

## 请求链路

```text
HTTP 请求
  -> RequestLoggingMiddleware
  -> 记录 JSON 日志
  -> 增加 Counter 和 Histogram
  -> FastAPI 返回响应
  -> Prometheus 定期抓取 /metrics
```

当前使用 Python `prometheus-client` 生成标准文本格式。指标接口不放进业务 OpenAPI 文档，避免把监控采集接口混入业务接口清单。

## 如何验证

启动服务后访问：

```text
http://127.0.0.1:8000/metrics
```

可以搜索：

```text
opspilot_http_requests_total
opspilot_http_request_duration_seconds
```

## 当前边界

指标暂存在单个进程内。多副本生产部署时，需要 Prometheus 分别抓取各副本，或使用合适的聚合方案。当前还没有配置 Prometheus Server、告警规则和 Grafana 面板，不能把这些能力写成已完成。

下一步自动化巡检可以读取 `/healthz`、`/readyz` 和 `/metrics`，形成带证据的巡检报告。
