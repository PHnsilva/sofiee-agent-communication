from __future__ import annotations

import copy
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from agent_runtime.communication import execute
from agent_runtime.contracts import TOOLS, error_result
from agent_runtime.orchestration import run_task


def _task(stages, **options):
    return {"contractVersion": "1.0.0", "objective": "Processar uma solicitação de comunicação", "stages": stages, **options}


def _respond(text="Olá", session_id="session-test"):
    return dict(TOOLS["communication.respond"]["examples"]["validInput"], sessionId=session_id, text=text, history=[])


def _generated_respond(content):
    return {"locale": "pt-BR", "intent": "respond", "content": content, "entities": [], "clarificationQuestions": []}


def _generated_transform(text):
    return {"text": text, "preservedEntities": [], "uncertainSpans": []}


class CommunicationOrchestrationTests(unittest.TestCase):
    def test_direct_capability_runs_with_simulated_model_and_keeps_mode_explicit(self):
        calls = []

        def fixture(tool, payload, _cancel):
            calls.append((tool, payload))
            return execute(tool, payload, model=type("Model", (), {"generate_json": lambda *_args, **_kwargs: _generated_respond("Resposta simulada")})())

        result = run_task(_task([{"id": "reply", "tool": "communication.respond", "input": _respond()}]), execute_tool=fixture)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["executed"])
        self.assertEqual(result["stages"][0]["mode"], "simulated")
        self.assertEqual(result["stages"][0]["result"]["content"], "Resposta simulada")

    def test_direct_local_cli_path_reports_missing_model_without_external_handoff(self):
        result = run_task(_task([{"id": "reply", "tool": "communication.respond", "input": _respond()}]))
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["executed"])
        self.assertTrue(any("modelo local" in item for item in result["missingDependencies"]))
        self.assertEqual(result["stages"][0]["error"]["code"], "unavailable")

    def test_composed_reply_then_translation_uses_only_declared_output_field(self):
        outputs = iter([_generated_respond("A entrega é amanhã."), _generated_transform("Delivery is tomorrow.")])
        seen = []

        def fixture(tool, payload, _cancel):
            seen.append((tool, copy.deepcopy(payload)))
            return execute(tool, payload, model=type("Model", (), {"generate_json": lambda *_args, **_kwargs: next(outputs)})())

        transform = dict(TOOLS["communication.transform"]["examples"]["validInput"])
        transform["text"] = {"$resultFrom": "draft", "field": "content"}
        result = run_task(
            _task(
                [
                    {"id": "draft", "tool": "communication.respond", "input": _respond("Escreva uma nota curta.")},
                    {"id": "translation", "tool": "communication.transform", "dependsOn": ["draft"], "input": transform},
                ]
            ),
            execute_tool=fixture,
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(seen[1][1]["text"], "A entrega é amanhã.")
        self.assertEqual(result["stages"][1]["result"]["text"], "Delivery is tomorrow.")
        self.assertEqual({stage["mode"] for stage in result["stages"]}, {"simulated"})
        self.assertEqual(result["delegation"]["subagents"], 0)

    def test_voice_tools_are_blocked_as_unavailable_not_claimed_as_audio(self):
        request = dict(TOOLS["communication.transcribe"]["examples"]["validInput"])
        result = run_task(_task([{"id": "transcribe", "tool": "communication.transcribe", "input": request}]))
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("voz" in item for item in result["missingDependencies"]))
        self.assertEqual(result["stages"][0]["result"]["status"], "unavailable")
        self.assertFalse(result["executed"])

    def test_failed_dependency_blocks_consumer_but_independent_stage_continues(self):
        malformed = {"contractVersion": "invalid"}
        result = run_task(
            _task(
                [
                    {"id": "bad", "tool": "communication.respond", "input": malformed},
                    {"id": "dependent", "tool": "communication.transform", "dependsOn": ["bad"], "input": dict(TOOLS["communication.transform"]["examples"]["validInput"])},
                    {"id": "independent", "tool": "communication.cancelTurn", "input": dict(TOOLS["communication.cancelTurn"]["examples"]["validInput"])},
                ]
            )
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual([stage["status"] for stage in result["stages"]], ["failed", "blocked", "completed"])
        self.assertEqual(result["stages"][1]["blockedBy"], ["bad"])

    def test_unknown_tools_duplicate_ids_forward_edges_and_unlisted_references_fail_closed(self):
        first = {"id": "a", "tool": "communication.respond", "input": _respond()}
        cases = [
            [{"id": "a", "tool": "shell", "input": {}}],
            [first, first],
            [{"id": "a", "tool": "communication.respond", "dependsOn": ["later"], "input": _respond()}],
            [first, {"id": "b", "tool": "communication.transform", "input": {**TOOLS["communication.transform"]["examples"]["validInput"], "text": {"$resultFrom": "a", "field": "content"}}}],
        ]
        for stages in cases:
            with self.subTest(stages=stages):
                self.assertEqual(run_task(_task(stages))["code"], "invalid_request")

    def test_retries_only_explicit_retryable_error_and_caps_attempts(self):
        calls = 0

        def fixture(tool, payload, _cancel):
            nonlocal calls
            calls += 1
            if calls == 1:
                return error_result("unavailable", "fixture interruption", retryable=True)
            return execute(tool, payload, model=type("Model", (), {"generate_json": lambda *_args, **_kwargs: _generated_respond("OK")})())

        result = run_task(
            _task([{"id": "reply", "tool": "communication.respond", "input": _respond()}], limits={"maxAttempts": 2}),
            execute_tool=fixture,
        )
        self.assertEqual(calls, 2)
        self.assertEqual(result["stages"][0]["attempts"], 2)
        self.assertEqual(result["status"], "completed")

    def test_cancel_timeout_and_task_limits_are_visible(self):
        cancelled = threading.Event()
        cancelled.set()
        request = _task([{"id": "reply", "tool": "communication.respond", "input": _respond()}])
        result = run_task(request, cancel_event=cancelled)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["stages"][0]["status"], "cancelled")

        ticks = iter([0.0, 0.0, 0.0, 2.0, 2.0])
        timed = run_task(
            _task([{"id": "voice", "tool": "communication.transcribe", "input": dict(TOOLS["communication.transcribe"]["examples"]["validInput"])}], limits={"timeoutMs": 1000}),
            clock=lambda: next(ticks, 2.0),
        )
        self.assertEqual(timed["status"], "timed_out")
        self.assertEqual(run_task(_task([request["stages"][0]] * 2, limits={"maxSteps": 1}))["code"], "invalid_request")

    def test_checkpoint_resumes_untrusted_output_without_repeating_completed_step(self):
        task = _task([{"id": "reply", "tool": "communication.respond", "input": _respond()}])
        fake = lambda tool, payload, _cancel: execute(tool, payload, model=type("Model", (), {"generate_json": lambda *_args, **_kwargs: _generated_respond("Resposta")})())
        first = run_task(task, execute_tool=fake)
        second = run_task({**task, "resume": first["checkpoint"]}, execute_tool=lambda *_args: self.fail("must reuse validated checkpoint"))
        self.assertEqual(second["taskId"], first["taskId"])
        self.assertEqual(second["stages"][0]["mode"], "checkpoint_untrusted")
        self.assertFalse(second["executed"])

    def test_simultaneous_requests_keep_session_and_context_isolated(self):
        def invoke(text, session):
            fake = lambda tool, payload, _cancel: execute(tool, payload, model=type("Model", (), {"generate_json": lambda *_args, **_kwargs: _generated_respond(text)})())
            return run_task(_task([{"id": "reply", "tool": "communication.respond", "input": _respond(text, session)}]), execute_tool=fake)

        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = list(pool.map(lambda pair: invoke(*pair), [("Resposta A", "session-a"), ("Resposta B", "session-b")]))
        self.assertNotEqual(a["taskId"], b["taskId"])
        self.assertEqual(a["stages"][0]["result"]["content"], "Resposta A")
        self.assertEqual(b["stages"][0]["result"]["content"], "Resposta B")


if __name__ == "__main__":
    unittest.main()
