"""SLO 快照计算：把 Prometheus HTTP 指标转换为可解释的可靠性结论。"""

from dataclasses import dataclass
import math
import os
from typing import Any

from app.metrics import http_request_duration_seconds, http_requests_total


@dataclass(frozen=True)
class SLOConfig:
    availability_target_percent: float = 99.9
    p95_latency_target_ms: float = 500.0

    def __post_init__(self) -> None:
        if not 0 < self.availability_target_percent < 100:
            raise ValueError("availability_target_percent 必须大于 0 且小于 100")
        if self.p95_latency_target_ms <= 0:
            raise ValueError("p95_latency_target_ms 必须大于 0")

    @classmethod
    def from_env(cls) -> "SLOConfig":
        return cls(
            availability_target_percent=float(os.getenv("OPSPILOT_SLO_AVAILABILITY", "99.9")),
            p95_latency_target_ms=float(os.getenv("OPSPILOT_SLO_P95_MS", "500")),
        )


def evaluate_slo(
    total_requests: int,
    failed_requests: int,
    p95_latency_ms: float | None,
    config: SLOConfig | None = None,
) -> dict[str, Any]:
    """根据窗口内快照计算可用性、错误预算和延迟是否达标。"""
    target = config or SLOConfig()
    if total_requests < 0 or failed_requests < 0 or failed_requests > total_requests:
        raise ValueError("请求数必须非负，且失败请求数不能超过总请求数")
    if total_requests <= 0:
        return {
            "status": "no_data",
            "availability_percent": None,
            "error_rate_percent": None,
            "error_budget_percent": round(100 - target.availability_target_percent, 4),
            "error_budget_consumed_percent": None,
            "p95_latency_ms": p95_latency_ms,
        }

    availability = (total_requests - failed_requests) / total_requests * 100
    error_rate = failed_requests / total_requests * 100
    budget = max(0.0, 100 - target.availability_target_percent)
    consumed = (error_rate / budget * 100) if budget else (0.0 if failed_requests == 0 else math.inf)
    latency_pass = p95_latency_ms is not None and p95_latency_ms <= target.p95_latency_target_ms
    status = "no_data" if p95_latency_ms is None else (
        "pass" if availability >= target.availability_target_percent and latency_pass else "fail"
    )
    return {
        "status": status,
        "availability_percent": round(availability, 4),
        "error_rate_percent": round(error_rate, 4),
        "error_budget_percent": round(budget, 4),
        "error_budget_consumed_percent": round(consumed, 4) if math.isfinite(consumed) else None,
        "p95_latency_ms": p95_latency_ms,
    }


def _is_business_request(path: str) -> bool:
    """SLO 只统计用户业务接口，排除健康探针、巡检和页面自身请求。"""
    return path.startswith("/api/v1/activities/")


def _histogram_p95_ms() -> float | None:
    """按所有接口聚合 Histogram bucket，计算近似 P95；没有请求时返回 None。"""
    buckets: dict[float, float] = {}
    total = 0.0
    for family in http_request_duration_seconds.collect():
        for sample in family.samples:
            if not sample.name.endswith("_bucket"):
                continue
            if not _is_business_request(sample.labels.get("path", "")):
                continue
            upper_bound = sample.labels.get("le")
            if upper_bound == "+Inf":
                total += sample.value
            else:
                buckets[float(upper_bound)] = buckets.get(float(upper_bound), 0.0) + sample.value
    if total <= 0 or not buckets:
        return None
    target = total * 0.95
    for upper_bound in sorted(buckets):
        if buckets[upper_bound] >= target:
            return round(upper_bound * 1000, 2)
    return None


def slo_snapshot() -> dict[str, Any]:
    """读取当前进程累计 HTTP 指标，返回可供接口和 Agent 使用的结构化结果。"""
    total_requests = 0
    failed_requests = 0
    for family in http_requests_total.collect():
        for sample in family.samples:
            if not sample.name.endswith("_total"):
                continue
            if not _is_business_request(sample.labels.get("path", "")):
                continue
            count = int(sample.value)
            total_requests += count
            if str(sample.labels.get("status", "")).startswith("5"):
                failed_requests += count

    config = SLOConfig.from_env()
    result = evaluate_slo(total_requests, failed_requests, _histogram_p95_ms(), config)
    return {
        "window": "process_lifetime",
        "targets": {
            "availability_percent": config.availability_target_percent,
            "p95_latency_ms": config.p95_latency_target_ms,
        },
        "observed": {
            "total_requests": total_requests,
            "failed_requests": failed_requests,
        },
        **result,
    }
