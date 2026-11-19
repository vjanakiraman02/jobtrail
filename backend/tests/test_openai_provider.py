"""Exercises the real OpenAI client against a local fake of the chat-completions API.

No network and no API key: a tiny HTTP server on localhost plays the model, so the
request the client actually sends (JSON mode, temperature, auth) can be checked.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.extraction.providers import OpenAICompatibleProvider, ProviderError
from app.extraction.service import extract_job

GOOD = {
    "company": "Acme Cloud",
    "title": "Backend Engineer",
    "location": None,
    "work_mode": "remote",
    "salary_range": None,
    "required_skills": ["Go", "PostgreSQL"],
}


class FakeOpenAIServer:
    def __init__(self):
        self.requests: list[dict] = []
        self.headers: list[dict] = []
        self.reject_temperature = False
        self.status = 200
        self.content = json.dumps(GOOD)
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                # HTTP header names are case-insensitive; normalize so tests can look them up.
                outer.headers.append({k.lower(): v for k, v in self.headers.items()})
                if outer.status != 200:
                    self._send(outer.status, {"error": {"message": "model not found"}})
                elif outer.reject_temperature and "temperature" in body:
                    self._send(
                        400,
                        {"error": {"message": "Unsupported value: 'temperature' is not supported"}},
                    )
                else:
                    self._send(
                        200,
                        {
                            "id": "x",
                            "object": "chat.completion",
                            "created": 0,
                            "model": body["model"],
                            "choices": [
                                {
                                    "index": 0,
                                    "finish_reason": "stop",
                                    "message": {"role": "assistant", "content": outer.content},
                                }
                            ],
                        },
                    )

            def _send(self, status, payload):
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture()
def fake_api():
    server = FakeOpenAIServer()
    yield server
    server.close()


def make_provider(fake_api, **overrides):
    return OpenAICompatibleProvider(
        model="test-model", api_key="test-key", base_url=fake_api.url, timeout=5, **overrides
    )


def test_sends_json_mode_request_and_returns_content(fake_api):
    provider = make_provider(fake_api)
    reply = provider.complete_json(system="SYS", user="USER")
    assert json.loads(reply) == GOOD

    sent = fake_api.requests[0]
    assert sent["model"] == "test-model"
    assert sent["response_format"] == {"type": "json_object"}
    assert sent["temperature"] == 0
    assert sent["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USER"},
    ]
    assert fake_api.headers[0]["authorization"] == "Bearer test-key"


def test_full_extraction_through_the_real_client(fake_api):
    job = extract_job(
        "Acme Cloud is hiring a remote Backend Engineer. Go, PostgreSQL.", make_provider(fake_api)
    )
    assert job.company == "Acme Cloud"
    assert job.work_mode == "remote"
    assert job.required_skills == ["Go", "PostgreSQL"]


def test_retries_without_temperature_when_model_rejects_it(fake_api):
    fake_api.reject_temperature = True
    reply = make_provider(fake_api).complete_json(system="s", user="u")
    assert json.loads(reply) == GOOD
    assert len(fake_api.requests) == 2
    assert "temperature" in fake_api.requests[0]
    assert "temperature" not in fake_api.requests[1]


def test_api_errors_become_provider_errors(fake_api):
    fake_api.status = 404
    with pytest.raises(ProviderError, match="model not found"):
        make_provider(fake_api).complete_json(system="s", user="u")


def test_empty_reply_is_a_provider_error(fake_api):
    fake_api.content = ""
    with pytest.raises(ProviderError, match="empty"):
        make_provider(fake_api).complete_json(system="s", user="u")


def test_unreachable_server_is_a_provider_error(fake_api):
    provider = make_provider(fake_api)
    fake_api.close()
    with pytest.raises(ProviderError):
        provider.complete_json(system="s", user="u")
