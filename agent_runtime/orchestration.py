"""Request-scoped task coordination over the existing communication tools."""

from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .communication import execute
from .contracts import CONTRACT, ERROR_SCHEMA, ContractViolation, error_result, validate, validate_result


ROOT = Path(__file__).resolve().parents[1]
TASK_SCHEMA = json.loads((ROOT / "contracts" / "v1" / "task.schema.json").read_text(encoding="utf-8"))
TASK_RESULT_SCHEMA = json.loads(
    (ROOT / "contracts" / "v1" / "task-result.schema.json").read_text(encoding="utf-8")
)
TASK_TOOLS = {
    "communication.respond",
    "communication.transform",
    "communication.transcribe",
    "communication.synthesize",
    "communication.cancelTurn",
}
_DEFAULT_LIMITS = {
    "maxSteps": 8,
    "timeoutMs": 60_000,
    "maxAttempts": 1,
    "maxConcurrency": 1,
    "maxDelegationDepth": 0,
}
_Runner = Callable[[str, dict[str, Any], threading.Event | None], dict[str, Any]]


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _stage_digest(stage: dict[str, Any]) -> str:
    return _digest(
        {
            "id": stage["id"],
            "tool": stage["tool"],
            "input": stage["input"],
            "dependsOn": stage.get("dependsOn", []),
        }
    )


def _definition(task: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    return {
        "contractVersion": task["contractVersion"],
        "objective": task["objective"],
        "stages": [
            {"id": stage["id"], "tool": stage["tool"], "input": stage["input"], "dependsOn": stage.get("dependsOn", [])}
            for stage in task["stages"]
        ],
        "limits": limits,
    }


def _references(value: Any) -> set[tuple[str, str]]:
    if isinstance(value, list):
        return set().union(*(_references(item) for item in value)) if value else set()
    if isinstance(value, dict):
        if "$resultFrom" in value:
            if set(value) != {"$resultFrom", "field"} or not all(isinstance(value[key], str) for key in value):
                raise ContractViolation("Result references require only a stage ID and output field")
            return {(value["$resultFrom"], value["field"])}
        return set().union(*(_references(item) for item in value.values())) if value else set()
    return set()


def _resolve(value: Any, results: dict[str, dict[str, Any]]) -> Any:
    if isinstance(value, list):
        return [_resolve(item, results) for item in value]
    if isinstance(value, dict):
        if "$resultFrom" in value:
            if set(value) != {"$resultFrom", "field"}:
                raise ContractViolation("Result references require only a stage ID and output field")
            stage_id = value["$resultFrom"]
            field = value["field"]
            result = results.get(stage_id)
            if result is None or field not in result:
                raise ContractViolation("Referenced stage result field is unavailable")
            return copy.deepcopy(result[field])
        return {key: _resolve(item, results) for key, item in value.items()}
    return value


def _validate_graph(stages: list[dict[str, Any]], limits: dict[str, int]) -> None:
    if len(stages) > limits["maxSteps"]:
        raise ContractViolation("Task exceeds maxSteps")
    prior: set[str] = set()
    for stage in stages:
        if stage["id"] in prior:
            raise ContractViolation("Stage IDs must be unique")
        if stage["tool"] not in TASK_TOOLS:
            raise ContractViolation("Task tool is not available")
        dependencies = stage.get("dependsOn", [])
        if len(dependencies) != len(set(dependencies)):
            raise ContractViolation("Stage dependencies must be unique")
        if any(dependency not in prior for dependency in dependencies):
            raise ContractViolation("Dependencies must reference earlier stages")
        refs = _references(stage["input"])
        if not {stage_id for stage_id, _ in refs}.issubset(set(dependencies)):
            raise ContractViolation("Every result reference must be declared as a dependency")
        prior.add(stage["id"])


def _mode(tool: str, simulated: bool) -> str:
    if simulated:
        return "simulated"
    if tool in {"communication.respond", "communication.transform"}:
        return "local_model"
    if tool in {"communication.transcribe", "communication.synthesize"}:
        return "local_capability"
    return "deterministic"


def _stage_outcome(tool: str, result: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    missing_dependencies: list[str] = []
    missing_inputs: list[str] = []
    if "code" in result:
        if result["code"] == "unavailable":
            missing_dependencies.append(
                "modelo local opt-in para texto" if tool in {"communication.respond", "communication.transform"}
                else "capacidade local de áudio configurada para a ferramenta solicitada"
            )
            return "blocked", missing_dependencies, missing_inputs
        if result["code"] in {"context_limit", "ambiguous_request"}:
            missing_inputs.append(result["message"])
            return "needs_input", missing_dependencies, missing_inputs
        return "failed", missing_dependencies, missing_inputs
    if result.get("status") == "unavailable":
        missing_dependencies.append("provedor local de voz ainda não implementado/configurado")
        return "blocked", missing_dependencies, missing_inputs
    if result.get("status") == "needs_clarification":
        missing_inputs.extend(result.get("clarificationQuestions", []))
        return "needs_input", missing_dependencies, missing_inputs
    return "completed", missing_dependencies, missing_inputs


def run_task(
    payload: Any,
    *,
    execute_tool: _Runner | None = None,
    cancel_event: threading.Event | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Run contracted communication capabilities serially without storing user data."""
    try:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(encoded) > 80_000:
            return error_result("context_limit", "Task exceeds 80000 bytes.")
        validate(TASK_SCHEMA, payload)
        limits = dict(_DEFAULT_LIMITS)
        limits.update(payload.get("limits", {}))
        _validate_graph(payload["stages"], limits)
        definition = _definition(payload, limits)
        definition_digest = _digest(definition)
        task_id = str(uuid.UUID(payload.get("resume", {}).get("taskId", str(uuid.uuid4()))))
        definitions = {stage["id"]: stage for stage in payload["stages"]}
        resumed: dict[str, dict[str, Any]] = {}
        if payload.get("resume"):
            checkpoint = payload["resume"]
            if checkpoint["objectiveDigest"] != definition_digest:
                raise ContractViolation("Checkpoint belongs to a different task definition")
            for item in checkpoint["completedStages"]:
                if item["id"] in resumed:
                    raise ContractViolation("Checkpoint stage IDs must be unique")
                stage = definitions.get(item["id"])
                if stage is None or item["tool"] != stage["tool"] or item["stageDigest"] != _stage_digest(stage):
                    raise ContractViolation("Checkpoint stage does not match the current task")
                validate_result(item["tool"], item["result"])
                resumed[item["id"]] = item
    except (ContractViolation, KeyError, TypeError, ValueError, RecursionError) as exc:
        return error_result("invalid_request", str(exc) or "Task contract is invalid")

    runner = execute_tool or (lambda tool, data, event: execute(tool, data, cancel_event=event))
    started = clock()
    results: dict[str, dict[str, Any]] = {}
    states: dict[str, str] = {}
    output_stages: list[dict[str, Any]] = []
    missing_dependencies: list[str] = []
    missing_inputs: list[str] = []
    stop_status: str | None = None

    for stage in payload["stages"]:
        if cancel_event is not None and cancel_event.is_set():
            stop_status = "cancelled"
            break
        if clock() - started >= limits["timeoutMs"] / 1000:
            stop_status = "timed_out"
            break
        stage_id = stage["id"]
        tool = stage["tool"]
        if stage_id in resumed:
            item = resumed[stage_id]
            results[stage_id] = item["result"]
            states[stage_id] = "completed"
            output_stages.append(
                {"id": stage_id, "tool": tool, "status": "completed", "mode": "checkpoint_untrusted", "attempts": 0, "result": item["result"]}
            )
            continue
        blocked_by = [dependency for dependency in stage.get("dependsOn", []) if states.get(dependency) != "completed"]
        if blocked_by:
            states[stage_id] = "blocked"
            output_stages.append(
                {"id": stage_id, "tool": tool, "status": "blocked", "mode": "deterministic", "attempts": 0, "blockedBy": blocked_by}
            )
            continue
        mode = _mode(tool, execute_tool is not None)
        record: dict[str, Any] = {"id": stage_id, "tool": tool, "status": "failed", "mode": mode, "attempts": 0}
        try:
            stage_input = _resolve(stage["input"], results)
            if not isinstance(stage_input, dict):
                raise ContractViolation("Resolved stage input must be an object")
            for attempt in range(1, limits["maxAttempts"] + 1):
                if cancel_event is not None and cancel_event.is_set():
                    stop_status = "cancelled"
                    record["status"] = "cancelled"
                    break
                if clock() - started >= limits["timeoutMs"] / 1000:
                    stop_status = "timed_out"
                    record["status"] = "timed_out"
                    break
                record["attempts"] = attempt
                try:
                    result = runner(tool, stage_input, cancel_event)
                except KeyboardInterrupt:
                    stop_status = "cancelled"
                    record["status"] = "cancelled"
                    break
                if not isinstance(result, dict):
                    result = error_result("internal_error", "Tool returned a non-object result")
                if "code" in result:
                    try:
                        validate(ERROR_SCHEMA, result)
                    except ContractViolation:
                        result = error_result("internal_error", "Tool error failed its output contract")
                    outcome, absent, unanswered = _stage_outcome(tool, result)
                    record["error"] = result
                    record["status"] = outcome
                    missing_dependencies.extend(absent)
                    missing_inputs.extend(unanswered)
                    if result.get("retryable") is True and attempt < limits["maxAttempts"]:
                        continue
                    break
                try:
                    validate_result(tool, result)
                except ContractViolation:
                    record["error"] = error_result("internal_error", "Tool result failed its output contract")
                    record["status"] = "failed"
                    break
                if cancel_event is not None and cancel_event.is_set():
                    stop_status = "cancelled"
                    record["status"] = "cancelled"
                    break
                if clock() - started >= limits["timeoutMs"] / 1000:
                    stop_status = "timed_out"
                    record["status"] = "timed_out"
                    break
                outcome, absent, unanswered = _stage_outcome(tool, result)
                record["status"] = outcome
                record["result"] = result
                missing_dependencies.extend(absent)
                missing_inputs.extend(unanswered)
                if outcome == "completed":
                    results[stage_id] = result
                break
            states[stage_id] = record["status"]
            output_stages.append(record)
            if stop_status:
                break
        except (ContractViolation, KeyError, TypeError, ValueError, RecursionError) as exc:
            states[stage_id] = "failed"
            output_stages.append(
                {"id": stage_id, "tool": tool, "status": "failed", "mode": mode, "attempts": 0, "error": error_result("invalid_request", str(exc) or "Stage input is invalid")}
            )

    if stop_status:
        for stage in payload["stages"][len(output_stages):]:
            output_stages.append(
                {"id": stage["id"], "tool": stage["tool"], "status": stop_status, "mode": "deterministic", "attempts": 0}
            )
    stage_states = [stage["status"] for stage in output_stages]
    has_failure = any(state in {"failed", "blocked"} for state in stage_states)
    has_completed = any(state == "completed" for state in stage_states)
    if stop_status:
        status = stop_status
    elif has_failure and has_completed:
        status = "partial"
    elif has_failure:
        status = "blocked" if all(state == "blocked" for state in stage_states) else "failed"
    elif any(state == "needs_input" for state in stage_states):
        status = "needs_input"
    else:
        status = "completed"
    checkpoint = {
        "contractVersion": CONTRACT["contractVersion"],
        "taskId": task_id,
        "objectiveDigest": definition_digest,
        "completedStages": [
            {"id": stage["id"], "tool": stage["tool"], "stageDigest": _stage_digest(definitions[stage["id"]]), "result": stage["result"]}
            for stage in output_stages
            if stage["status"] == "completed" and "result" in stage
        ],
    }
    response = {
        "contractVersion": CONTRACT["contractVersion"],
        "taskId": task_id,
        "objective": payload["objective"],
        "status": status,
        "executed": any(stage["status"] == "completed" and stage["mode"] != "checkpoint_untrusted" for stage in output_stages),
        "stages": output_stages,
        "missingDependencies": sorted(set(missing_dependencies)),
        "missingInputs": missing_inputs,
        "limits": limits,
        "delegation": {"depthUsed": 0, "subagents": 0, "reason": "Consultas e ferramentas são chamadas sequenciais no mesmo processo; não há workers isolados."},
        "checkpoint": checkpoint,
    }
    validate(TASK_RESULT_SCHEMA, response)
    return response
