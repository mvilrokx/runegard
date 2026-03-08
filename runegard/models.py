from dataclasses import dataclass, field
from enum import Enum


class StepType(Enum):
    DIAGNOSTIC = "diagnostic"
    REMEDIATION = "remediation"
    VERIFICATION = "verification"
    ESCALATION = "escalation"


@dataclass
class Command:
    raw: str
    requires_approval: bool = False


@dataclass
class RunbookStep:
    id: str
    title: str
    step_type: StepType
    commands: list[Command] = field(default_factory=list)
    expected_output: str | None = None
    branches: dict[str, str] = field(default_factory=dict)
    next_step: str | None = None
    rollback_command: str | None = None


@dataclass
class Runbook:
    title: str
    trigger: str
    service: str
    steps: dict[str, RunbookStep] = field(default_factory=dict)
    first_step: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int
    command: str
    duration_ms: int
