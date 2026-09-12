"""Use the actual SDK request serializer without a network call."""
import json
from unittest.mock import AsyncMock
import anthropic
import httpx2
from core import utils


async def test_claude_sdk_serializes_sampling_parameter(monkeypatch):
    requests = []
    async def respond(request):
        requests.append(json.loads(request.content))
        return httpx2.Response(200, json={
            "id": "msg_test", "type": "message", "role": "assistant",
            "model": "claude-sonnet-4-6", "content": [{"type": "text", "text": "ok"}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        })
    async with anthropic.AsyncAnthropic(api_key="test-only", http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(respond))) as client:
        monkeypatch.setattr(utils, "_anthropic_client", client)
        monkeypatch.setattr("services.cost_tracker.record_claude", AsyncMock())
        assert await utils.claude_api_call("test", temperature=0) == "ok"
    assert requests[0]["temperature"] == 0
