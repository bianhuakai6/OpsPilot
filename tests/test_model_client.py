import json

import pytest

from app.config import Settings
from app.model_client import ModelClientError, request_response


class FakeResponse:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_responses_client_sends_bearer_and_extracts_native_output() -> None:
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse({"id": "resp-test", "model": "gpt-5.6-terra", "output": [{"content": [{"text": "分析结果"}]}]})

    result = request_response("prompt", Settings(model_api_key="secret"), opener=opener)

    assert result == {"text": "分析结果", "response_id": "resp-test", "model": "gpt-5.6-terra"}
    assert captured["url"] == "https://api.aircode.xin/responses"
    assert captured["auth"] == "Bearer secret"
    assert captured["body"]["store"] is False


def test_model_client_requires_key() -> None:
    with pytest.raises(ModelClientError, match="未配置"):
        request_response("prompt", Settings())
