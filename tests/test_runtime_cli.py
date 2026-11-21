from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent_runtime.contracts import TOOLS


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "run_runtime.py"


class RuntimeCliTests(unittest.TestCase):
    def test_task_entry_executes_deterministic_capability_and_reports_missing_model(self):
        task = {
            "contractVersion": "1.0.0",
            "objective": "Consultar o estado de cancelamento do turno",
            "stages": [{
                "id": "cancel",
                "tool": "communication.cancelTurn",
                "input": TOOLS["communication.cancelTurn"]["examples"]["validInput"],
            }],
        }
        completed = subprocess.run(
            [sys.executable, str(CLI)],
            input=json.dumps({"task": task}),
            text=True,
            capture_output=True,
            cwd=ROOT,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["executed"])
        self.assertEqual(result["stages"][0]["result"]["status"], "not_found")

        blocked_task = {
            "contractVersion": "1.0.0",
            "objective": "Responder em português sem modelo local",
            "stages": [{
                "id": "reply",
                "tool": "communication.respond",
                "input": dict(TOOLS["communication.respond"]["examples"]["validInput"], history=[]),
            }],
        }
        blocked = subprocess.run(
            [sys.executable, str(CLI)],
            input=json.dumps({"task": blocked_task}),
            text=True,
            capture_output=True,
            cwd=ROOT,
            timeout=5,
            check=False,
        )
        self.assertEqual(blocked.returncode, 0, blocked.stderr)
        self.assertEqual(json.loads(blocked.stdout)["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
