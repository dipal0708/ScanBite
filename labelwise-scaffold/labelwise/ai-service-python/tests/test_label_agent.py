import json
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.agents.label_agent import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    _ollama_chat,
    _chat,
    answer_followup,
    explain_scan,
)


def _fake_completion(content: str) -> bytes:
    return json.dumps(
        {"choices": [{"message": {"content": content}}]}
    ).encode("utf-8")


def _fake_response(payload: bytes) -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value.read.return_value = payload
    return response


class LabelAgentTests(unittest.TestCase):
    @patch("app.agents.label_agent._ollama_chat")
    def test_explain_scan_parses_expected_json(self, ollama_chat):
        ollama_chat.return_value = json.dumps(
            {"summary": "This fits your diet.", "suggestions": ["Compare sodium levels."]}
        )

        result = explain_scan({"scores": {"label": 85}})

        self.assertEqual(result["summary"], "This fits your diet.")
        self.assertEqual(result["suggestions"], ["Compare sodium levels."])
        ollama_chat.assert_called_once()

    @patch("app.agents.label_agent._ollama_chat")
    def test_explain_scan_rejects_invalid_response_shape(self, ollama_chat):
        ollama_chat.return_value = json.dumps({"summary": "No suggestions field."})

        with self.assertRaises(HTTPException) as raised:
            explain_scan({})

        self.assertEqual(raised.exception.status_code, 502)

    @patch("app.agents.label_agent._ollama_chat")
    def test_explain_scan_accepts_code_fenced_json(self, ollama_chat):
        payload = {"summary": "Wrapped in fences.", "suggestions": ["One tip."]}
        ollama_chat.return_value = f"```json\n{json.dumps(payload)}\n```"

        result = explain_scan({})

        self.assertEqual(result, payload)

    @patch("app.agents.label_agent._ollama_chat")
    def test_followup_returns_local_model_answer(self, ollama_chat):
        ollama_chat.return_value = "It has 12 grams of sugar."

        result = answer_followup({"nutrition": {"sugar_g": 12}}, "How much sugar?")

        self.assertEqual(result, {"answer": "It has 12 grams of sugar."})

    @patch("app.agents.label_agent.urlopen")
    def test_chat_uses_local_ollama_chat_api(self, urlopen):
        urlopen.return_value = _fake_response(
            json.dumps({"message": {"content": "Local response"}}).encode("utf-8")
        )

        content = _ollama_chat("Explain this scan.", num_predict=400, json_mode=True)

        self.assertEqual(content, "Local response")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, f"{OLLAMA_BASE_URL}/api/chat")
        body = json.loads(request.data)
        self.assertEqual(body["model"], OLLAMA_MODEL)
        self.assertFalse(body["stream"])
        self.assertEqual(body["format"], "json")


class ProviderDispatchTests(unittest.TestCase):
    @patch("app.agents.label_agent.LLM_PROVIDER", "ollama")
    @patch("app.agents.label_agent._ollama_chat")
    @patch("app.agents.label_agent._openai_chat")
    def test_default_provider_routes_to_ollama(self, openai_chat, ollama_chat):
        ollama_chat.return_value = "ok"

        result = _chat("hi", num_predict=10, json_mode=True)

        self.assertEqual(result, "ok")
        ollama_chat.assert_called_once_with("hi", num_predict=10, json_mode=True)
        openai_chat.assert_not_called()

    @patch("app.agents.label_agent.LLM_PROVIDER", "openai")
    @patch("app.agents.label_agent._ollama_chat")
    @patch("app.agents.label_agent._openai_chat")
    def test_openai_provider_routes_to_hosted_api(self, openai_chat, ollama_chat):
        openai_chat.return_value = "hosted"

        result = _chat("hi", num_predict=10)

        self.assertEqual(result, "hosted")
        openai_chat.assert_called_once_with("hi", num_predict=10, json_mode=False)
        ollama_chat.assert_not_called()

    @patch("app.agents.label_agent.LLM_PROVIDER", "something_else")
    def test_unknown_provider_returns_503(self):
        with self.assertRaises(HTTPException) as raised:
            _chat("hi", num_predict=10)

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("LLM_PROVIDER", raised.exception.detail)


class OpenAIChatTests(unittest.TestCase):
    @patch("app.agents.label_agent.OPENAI_BASE_URL", "https://api.example.com/v1")
    @patch("app.agents.label_agent.OPENAI_MODEL", "test-model")
    @patch("app.agents.label_agent.OPENAI_API_KEY", "test-key")
    @patch("app.agents.label_agent.urlopen")
    def test_sends_bearer_auth_json_mode_and_parses_content(self, urlopen):
        from app.agents.label_agent import _openai_chat

        urlopen.return_value = _fake_response(_fake_completion("Hosted response."))

        content = _openai_chat("Explain this scan.", num_predict=500, json_mode=True)

        self.assertEqual(content, "Hosted response.")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.example.com/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        body = json.loads(request.data)
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(body["max_tokens"], 500)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["messages"][0]["role"], "system")

    @patch("app.agents.label_agent.OPENAI_BASE_URL", "https://api.example.com/v1")
    @patch("app.agents.label_agent.OPENAI_API_KEY", "test-key")
    @patch("app.agents.label_agent.urlopen")
    def test_retries_once_without_response_format_on_400(self, urlopen):
        from app.agents.label_agent import _openai_chat

        bad_request = HTTPError("https://api.example.com", 400, "Bad Request", {}, None)
        self.addCleanup(bad_request.close)
        urlopen.side_effect = [
            bad_request,
            _fake_response(_fake_completion('{"summary": "s", "suggestions": []}')),
        ]

        content = _openai_chat("Explain.", num_predict=500, json_mode=True)

        self.assertTrue(content.startswith("{"))
        self.assertEqual(urlopen.call_count, 2)
        first_body = json.loads(urlopen.call_args_list[0].args[0].data)
        second_body = json.loads(urlopen.call_args_list[1].args[0].data)
        self.assertIn("response_format", first_body)
        self.assertNotIn("response_format", second_body)

    @patch("app.agents.label_agent.OPENAI_API_KEY", "")
    def test_missing_api_key_returns_503(self):
        from app.agents.label_agent import _openai_chat

        with self.assertRaises(HTTPException) as raised:
            _openai_chat("Explain.", num_predict=500)

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("OPENAI_API_KEY", raised.exception.detail)

    @patch("app.agents.label_agent.OPENAI_BASE_URL", "https://api.example.com/v1")
    @patch("app.agents.label_agent.OPENAI_API_KEY", "test-key")
    @patch("app.agents.label_agent.urlopen")
    def test_unreachable_provider_returns_503(self, urlopen):
        from app.agents.label_agent import _openai_chat

        urlopen.side_effect = URLError("connection refused")

        with self.assertRaises(HTTPException) as raised:
            _openai_chat("Explain.", num_predict=500)

        self.assertEqual(raised.exception.status_code, 503)

    @patch("app.agents.label_agent.OPENAI_BASE_URL", "https://api.example.com/v1")
    @patch("app.agents.label_agent.OPENAI_API_KEY", "test-key")
    @patch("app.agents.label_agent.urlopen")
    def test_empty_completion_returns_502(self, urlopen):
        from app.agents.label_agent import _openai_chat

        urlopen.return_value = _fake_response(_fake_completion("   "))

        with self.assertRaises(HTTPException) as raised:
            _openai_chat("Explain.", num_predict=500)

        self.assertEqual(raised.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()
