# M2 本地 HTTP 压测基线

## 目的和边界

压测用来观察指定环境、接口和并发设置下的响应表现，帮助建立可重复比较的基线。它不是生产容量承诺，也不能只凭一次本地结果推断云上吞吐。当前工具仅发送 GET，不会创建预约或修改业务数据。

## 运行

服务启动后，在项目根目录执行：

```powershell
python scripts/load_test.py
```

默认对 `/healthz` 进行 15 秒、8 并发的请求。报告包含总请求数、成功/失败数、错误率、吞吐量、延迟 P50/P95/最大值和少量错误样例，默认保存在 `reports/generated/`。

也可以指定目标、时长、并发和报告路径：

```powershell
python scripts/load_test.py --url http://127.0.0.1:8000/api/v1/activities/activity-001 --duration 30 --workers 4 --output reports/generated/activity-read.json
```

P50 表示一半请求的延迟不高于此值；P95 表示 95% 请求不高于此值。失败请求包括非 2xx/3xx 响应和网络错误，脚本会返回状态码 `2`，便于自动化识别。

比较结果时应固定机器、应用版本、目标接口、时长、并发，以及 MySQL/Redis 等本地负载。该工具没有验证长时间稳定性、复杂用户行为、生产流量模型或独立压测机容量，不能把单个 RPS 数字当作系统容量结论。后续应结合应用指标、主机资源和数据库指标定位瓶颈。
