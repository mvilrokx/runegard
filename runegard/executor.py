"""FSM execution engine for parsed runbooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from runegard.k8s import execute as k8s_execute
from runegard.models import Runbook, RunbookStep, StepType
from runegard.tracer import Tracer


@dataclass
class ExecutionResult:
    status: str  # "success" | "partial" | "failed"
    steps_executed: list[str] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)
    approvals: dict[str, str] = field(default_factory=dict)


class Executor:
    def __init__(
        self,
        runbook: Runbook,
        dry_run: bool = False,
        trace_dir: Path | None = None,
        fake_outputs: dict[str, str] | None = None,
        fake_approvals: dict[str, str] | None = None,
    ):
        self.runbook = runbook
        self.dry_run = dry_run
        self.fake_outputs = fake_outputs or {}
        self.fake_approvals = fake_approvals or {}

        trace_path = (trace_dir or Path(".")) / "trace_log.json"
        self.tracer = Tracer(trace_path)

        self.result = ExecutionResult(status="success")

    def run(self) -> ExecutionResult:
        current_step_id: str | None = self.runbook.first_step

        while current_step_id:
            step = self.runbook.steps.get(current_step_id)
            if not step:
                break

            self.result.steps_executed.append(step.id)

            # Approval gate for remediation steps
            if step.step_type == StepType.REMEDIATION:
                approval = self._get_approval(step.id, step)
                self.result.approvals[step.id] = approval
                self.tracer.log_approval(step.id, approval)

                if approval == "skip":
                    current_step_id = step.next_step
                    continue
                elif approval == "abort":
                    self.result.status = "partial"
                    break

            # Execute commands
            combined_stdout = ""
            for cmd in step.commands:
                cmd_result = self._execute_command(step.id, cmd.raw)
                combined_stdout += cmd_result

                self.tracer.log_step(
                    step_id=step.id,
                    step_type=step.step_type.value,
                    command=cmd.raw,
                    stdout=cmd_result,
                    stderr="",
                    exit_code=0,
                    duration_ms=0,
                )

            self.result.outputs[step.id] = combined_stdout

            # Branch or continue
            next_step_id = self._resolve_next(step, combined_stdout)
            if next_step_id != step.next_step and next_step_id is not None:
                self.tracer.log_branch(
                    from_step=step.id,
                    to_step=next_step_id,
                    reason="Output matched branch pattern",
                )
            current_step_id = next_step_id

        self.tracer.finalize(self.result.status)
        return self.result

    def _execute_command(self, step_id: str, command: str) -> str:
        if step_id in self.fake_outputs:
            return self.fake_outputs[step_id]

        result = k8s_execute(command, dry_run=self.dry_run)
        return result.stdout

    def _get_approval(self, step_id: str, step: RunbookStep) -> str:
        if step_id in self.fake_approvals:
            return self.fake_approvals[step_id]

        print(f"\n{'=' * 60}")
        print(f"APPROVAL REQUIRED -- {step.title}")
        print(f"{'=' * 60}")
        for cmd in step.commands:
            print(f"  Command:  {cmd.raw}")
        if step.rollback_command:
            print(f"  Rollback: {step.rollback_command}")
        print()

        while True:
            choice = input("Type 'approve', 'skip', or 'abort': ").strip().lower()
            if choice in ("approve", "skip", "abort"):
                return choice
            print("Invalid choice. Please type 'approve', 'skip', or 'abort'.")

    def _resolve_next(self, step: RunbookStep, output: str) -> str | None:
        for pattern, target_step_id in step.branches.items():
            if pattern.lower() in output.lower():
                return target_step_id
        return step.next_step
