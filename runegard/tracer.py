"""Execution trace logger for RLM consumption."""

import json
from pathlib import Path


class Tracer:
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self._steps: list[dict] = []
        self._branches: list[dict] = []
        self._approvals: list[dict] = []

    def log_step(
        self,
        step_id: str,
        step_type: str,
        command: str,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_ms: int,
    ) -> None:
        self._steps.append(
            {
                "step_id": step_id,
                "step_type": step_type,
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "duration_ms": duration_ms,
            }
        )

    def log_branch(self, from_step: str, to_step: str, reason: str) -> None:
        self._branches.append(
            {
                "from_step": from_step,
                "to_step": to_step,
                "reason": reason,
            }
        )

    def log_approval(self, step_id: str, outcome: str) -> None:
        self._approvals.append(
            {
                "step_id": step_id,
                "outcome": outcome,
            }
        )

    def finalize(self, status: str) -> None:
        trace = {
            "status": status,
            "steps": self._steps,
            "branches": self._branches,
            "approvals": self._approvals,
        }
        self.output_path.write_text(json.dumps(trace, indent=2))
