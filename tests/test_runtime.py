from __future__ import annotations

import json
import threading
import unittest
from unittest.mock import patch

from agent_runtime.communication import execute
from agent_runtime.contracts import TOOLS, validate
from agent_runtime.local_model import LocalModel, ModelCallError


class FakeModel:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def generate_json(self, instruction, data, *, cancel_event=None):
        self.calls += 1
        return self.result


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _size):
        return json.dumps({"response": json.dumps({"ok": True})}).encode("utf-8")


class RuntimeTests(unittest.TestCase):
    def test_contract_valid_input_and_unknown_field_are_checked(self):
        valid = TOOLS["communication.respond"]["examples"]["validInput"]
        validate(TOOLS["communication.respond"]["inputSchema"], valid)
        invalid = dict(valid, private_permission=True)
        with self.assertRaises(ValueError):
            validate(TOOLS["communication.respond"]["inputSchema"], invalid)

    def test_structured_response_uses_one_inference_call(self):
        fake = FakeModel(
            {
                "locale": "pt-BR",
                "intent": "summarize",
                "content": "O aviso pede um resumo.",
                "entities": [],
                "clarificationQuestions": [],
            }
        )
        result = execute(
            "communication.respond",
            TOOLS["communication.respond"]["examples"]["validInput"],
            model=fake,
        )
        self.assertEqual(fake.calls, 1)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["content"], "O aviso pede um resumo.")

    def test_transform_marks_uncertain_output_for_review(self):
        fake = FakeModel({"text": "Delivery tomorrow.", "preservedEntities": [], "uncertainSpans": ["9h"]})
        result = execute(
            "communication.transform",
            TOOLS["communication.transform"]["examples"]["validInput"],
            model=fake,
        )
        self.assertEqual(result["status"], "needs_review")

    def test_media_and_cancel_handlers_do_not_call_model(self):
        fake = FakeModel({})
        for tool_name in ("communication.transcribe", "communication.synthesize"):
            result = execute(tool_name, TOOLS[tool_name]["examples"]["validInput"], model=fake)
            self.assertEqual(result["status"], "unavailable")
            self.assertEqual(result.get("transcript", result.get("mediaRef")), "")
        cancel = execute(
            "communication.cancelTurn",
            TOOLS["communication.cancelTurn"]["examples"]["validInput"],
            model=fake,
        )
        self.assertEqual(cancel["status"], "not_found")
        self.assertEqual(fake.calls, 0)

    def test_missing_model_has_no_remote_fallback(self):
        adapter = LocalModel(model=None)
        with self.assertRaises(ModelCallError) as raised:
            adapter.generate_json("instruction", {})
        self.assertEqual(raised.exception.code, "unavailable")

    def test_pre_cancelled_generation_does_not_call_a_model(self):
        cancelled = threading.Event()
        cancelled.set()
        adapter = LocalModel(model="local-model")
        with self.assertRaises(ModelCallError) as raised:
            adapter.generate_json("instruction", {}, cancel_event=cancelled)
        self.assertEqual(raised.exception.code, "unavailable")

    def test_input_limit_fails_before_network(self):
        adapter = LocalModel(model="local-model", max_input_chars=10)
        with self.assertRaises(ModelCallError) as raised:
            adapter.generate_json("instruction", {"text": "too long"})
        self.assertEqual(raised.exception.code, "limit_exceeded")

    def test_adapter_uses_only_loopback_and_requests_json(self):
        adapter = LocalModel(
            model="local-model",
            timeout_seconds=5,
            max_input_chars=1000,
            max_output_tokens=64,
        )
        with patch("agent_runtime.local_model.urllib.request.urlopen", return_value=FakeResponse()) as open_url:
            self.assertEqual(adapter.generate_json("instruction", {}), {"ok": True})
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/generate")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["format"], "json")
        self.assertEqual(body["options"]["num_ctx"], 2048)
        self.assertEqual(body["options"]["num_predict"], 64)
        self.assertEqual(body["keep_alive"], 0)

    def test_malformed_model_shape_returns_error(self):
        fake = FakeModel({"locale": "pt-BR"})
        result = execute(
            "communication.respond",
            TOOLS["communication.respond"]["examples"]["validInput"],
            model=fake,
        )
        self.assertEqual(result["code"], "unavailable")
        self.assertEqual(fake.calls, 1)


if __name__ == "__main__":
    unittest.main()
