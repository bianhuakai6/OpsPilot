"""Responses 原生协议客户端；只负责请求模型，不执行运维动作。"""

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import Settings


class ModelClientError(RuntimeError):
    """模型配置、网络或响应格式异常。"""


def _extract_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []) if isinstance(item, dict) else []:
            text = content.get("text") if isinstance(content, dict) else None
            if isinstance(text, str):
                chunks.append(text)
    if not chunks:
        raise ModelClientError("模型响应中没有可读取的文本")
    return "".join(chunks)


def request_response(
    prompt: str,
    settings: Settings,
    *,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    if not settings.model_api_key.strip():
        raise ModelClientError("OPSPILOT_MODEL_API_KEY 未配置")
    path = settings.model_responses_path.strip() or "/responses"
    if not path.startswith("/"):
        path = "/" + path
    url = settings.model_base_url.rstrip("/") + path
    body = json.dumps({
        "model": settings.model_name,
        "input": prompt,
        "store": False,
    }).encode("utf-8")
    request = Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {settings.model_api_key}",
        "Content-Type": "application/json",
    })
    try:
        with opener(request, timeout=settings.model_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ModelClientError(f"模型服务返回 HTTP {exc.code}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ModelClientError(f"模型请求失败: {type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise ModelClientError("模型响应不是 JSON 对象")
    return {"text": _extract_text(payload), "response_id": payload.get("id"), "model": payload.get("model", settings.model_name)}
