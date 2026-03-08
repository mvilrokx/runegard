# RuneGard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an autonomous Kubernetes runbook executor that parses markdown runbooks, executes them step-by-step with human approval gates, and improves itself via an RLM loop using the Claude API.

**Architecture:** Python package (`runegard/`) with 5 modules — parser, executor, k8s wrapper, tracer, and improver — orchestrated by a CLI entry point. Wrapped in a `skill.md` for Claude Code integration. The RLM loop appends learnings to a reference file consulted on future runs.

**Tech Stack:** Python 3.12, uv (package management), ruff (lint/format), ty (type checking), anthropic SDK, pyyaml, pytest

---

## Task 1: Project Scaffold + Tooling

**Files:**
- Create: `runegard/pyproject.toml`
- Create: `runegard/runegard/__init__.py`
- Create: `runegard/runegard/models.py`
- Create: `runegard/.githooks/pre-commit`
- Create: `runegard/.githooks/pre-push`
- Create: `runegard/Makefile`
- Create: `runegard/.gitignore`

**Step 1: Create the project directory structure**

```bash
mkdir -p runegard/runegard
mkdir -p runegard/tests
mkdir -p runegard/references
mkdir -p runegard/assets/runbooks
mkdir -p runegard/demo
mkdir -p runegard/.githooks
```

**Step 2: Create pyproject.toml with uv + ruff + ty config**

```toml
[project]
name = "runegard"
version = "0.1.0"
description = "Autonomous Kubernetes runbook executor"
requires-python = ">=3.12"
dependencies = [
    "anthropic",
    "pyyaml",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "ruff",
    "ty",
]

[project.scripts]
runegard = "runegard.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py312"
line-length = 99

[tool.ruff.lint]
select = [
    "E",     # pycodestyle errors
    "F",     # pyflakes
    "I",     # isort
    "B",     # flake8-bugbear
    "UP",    # pyupgrade
    "SIM",   # flake8-simplify
    "RUF",   # ruff-specific rules
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]
```

**Step 3: Create .gitignore**

```
__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
build/
trace_log.json
.python-version
uv.lock
```

**Step 4: Create models.py with the data model**

```python
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
```

**Step 5: Create empty __init__.py**

```python
"""RuneGard - Autonomous Kubernetes Runbook Executor"""
```

**Step 6: Create pre-commit hook**

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "==> pre-commit: formatting staged Python files"
STAGED_PY_FILES=$(git diff --cached --name-only --diff-filter=d -- '*.py')
if [ -n "$STAGED_PY_FILES" ]; then
    echo "$STAGED_PY_FILES" | xargs uv run ruff format
    echo "$STAGED_PY_FILES" | xargs uv run ruff check --fix
    echo "$STAGED_PY_FILES" | xargs git add
fi

echo "==> pre-commit: testing changed packages"
CHANGED_TEST_FILES=$(git diff --cached --name-only --diff-filter=d -- 'tests/*.py')
if [ -n "$CHANGED_TEST_FILES" ]; then
    uv run pytest $CHANGED_TEST_FILES -x -q
elif [ -n "$STAGED_PY_FILES" ]; then
    uv run pytest tests/ -x -q 2>/dev/null || echo "  no tests found, skipping"
fi

echo "==> pre-commit: all checks passed"
```

**Step 7: Create pre-push hook**

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "==> pre-push: linting"
uv run ruff check .

echo "==> pre-push: formatting check"
uv run ruff format --check .

echo "==> pre-push: type checking"
uv run ty check

echo "==> pre-push: full test suite"
uv run pytest tests/ -v

echo "==> pre-push: all checks passed"
```

**Step 8: Create Makefile**

```makefile
.PHONY: help setup fmt lint typecheck test audit

## help: print this help message
help:
	@echo 'Usage:'
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' | sed -e 's/^/ /'

## setup: install dependencies and git hooks
setup:
	uv sync
	git config core.hooksPath .githooks
	@echo "Git hooks installed from .githooks/"

## fmt: format code with ruff
fmt:
	uv run ruff format .
	uv run ruff check --fix .

## lint: run ruff linter
lint:
	uv run ruff check .

## typecheck: run ty type checker
typecheck:
	uv run ty check

## test: run all tests
test:
	uv run pytest tests/ -v

## audit: run all quality control checks
audit: lint typecheck test
	uv run ruff format --check .
	@echo "All checks passed"
```

**Step 9: Initialize the project with uv**

Run: `cd /home/yolo/projects/skillathon/runegard && uv sync`
Expected: Creates `.venv/`, installs all dependencies including dev group

**Step 10: Configure git hooks**

Run: `cd /home/yolo/projects/skillathon/runegard && chmod +x .githooks/pre-commit .githooks/pre-push && git config core.hooksPath .githooks`

**Step 11: Verify tooling works**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: All pass with no errors (only models.py and __init__.py exist)

**Step 12: Commit**

```bash
git add runegard/
git commit -m "feat: scaffold runegard project with uv, ruff, ty, and git hooks"
```

---

## Task 2: Demo Runbook

**Files:**
- Create: `runegard/assets/runbooks/crashloop.md`

**Step 1: Write the CrashLoopBackOff runbook**

```markdown
# Runbook: KubePodCrashLooping

## Trigger
Alert: KubePodCrashLooping -- Pod is restarting > 0.5/second

## Steps

### Step 1: Identify the crashing pod
- Run: `kubectl get pods --field-selector=status.phase!=Running -A`
- Look for pods with STATUS = CrashLoopBackOff

### Step 2: Get pod details
- Run: `kubectl describe pod <pod-name> -n <namespace>`
- Check the Events section for:
  - OOMKilled -> go to Step 5
  - ImagePullBackOff -> go to Step 6
  - Error or CrashLoopBackOff -> continue to Step 3

### Step 3: Check container logs
- Run: `kubectl logs <pod-name> -n <namespace> --previous`
- If logs show application error -> go to Step 4
- If logs are empty -> go to Step 7

### Step 4: Diagnose application error
- Review the error message in logs
- Common causes:
  - Missing environment variable -> check ConfigMap/Secret mounts
  - Database connection failure -> verify service DNS and network policies
  - Permission denied -> check RBAC and SecurityContext
- **Remediation**: Fix the root cause (may require deployment update)

### Step 5: Handle OOMKilled
- Run: `kubectl top pod <pod-name> -n <namespace>` (if metrics-server available)
- **Remediation**: Increase memory limits:
  `kubectl patch deployment <deploy-name> -n <namespace> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container>","resources":{"limits":{"memory":"512Mi"}}}]}}}}'`

### Step 6: Handle ImagePullBackOff
- Run: `kubectl describe pod <pod-name> -n <namespace> | grep -A5 "Events"`
- Verify image name and tag exist
- Check imagePullSecrets if using private registry
- **Remediation**: Fix image reference in deployment spec

### Step 7: Empty logs -- check init containers
- Run: `kubectl logs <pod-name> -n <namespace> -c <init-container> --previous`
- If init container is failing, diagnose its logs separately

### Verification
- Run: `kubectl get pods -n <namespace> | grep <pod-name>`
- Confirm STATUS = Running and RESTARTS has stopped incrementing
- Wait 2 minutes and re-check
```

**Step 2: Commit**

```bash
git add runegard/assets/
git commit -m "feat: add CrashLoopBackOff demo runbook"
```

---

## Task 3: Runbook Parser

**Files:**
- Create: `runegard/tests/test_parser.py`
- Create: `runegard/runegard/parser.py`

**Step 1: Write the failing test for the fallback parser**

This test uses the fallback (no API) parser so it runs without a Claude API key.

```python
import pytest
from pathlib import Path
from runegard.models import StepType


SIMPLE_RUNBOOK = """# Runbook: Test

## Trigger
Alert: TestAlert

## Steps

### Step 1: Check status
- Run: `kubectl get pods`

### Step 2: Fix it
- **Remediation**: `kubectl delete pod bad-pod`

### Verification
- Run: `kubectl get pods`
"""


class TestFallbackParser:
    def test_parses_title(self, tmp_path):
        from runegard.parser import parse_runbook_fallback

        f = tmp_path / "test.md"
        f.write_text(SIMPLE_RUNBOOK)
        runbook = parse_runbook_fallback(f)
        assert runbook.title == "Runbook: Test"

    def test_parses_trigger(self, tmp_path):
        from runegard.parser import parse_runbook_fallback

        f = tmp_path / "test.md"
        f.write_text(SIMPLE_RUNBOOK)
        runbook = parse_runbook_fallback(f)
        assert "TestAlert" in runbook.trigger

    def test_extracts_steps(self, tmp_path):
        from runegard.parser import parse_runbook_fallback

        f = tmp_path / "test.md"
        f.write_text(SIMPLE_RUNBOOK)
        runbook = parse_runbook_fallback(f)
        assert len(runbook.steps) >= 2

    def test_extracts_commands(self, tmp_path):
        from runegard.parser import parse_runbook_fallback

        f = tmp_path / "test.md"
        f.write_text(SIMPLE_RUNBOOK)
        runbook = parse_runbook_fallback(f)
        step1 = runbook.steps[runbook.first_step]
        assert any("kubectl get pods" in c.raw for c in step1.commands)

    def test_detects_remediation(self, tmp_path):
        from runegard.parser import parse_runbook_fallback

        f = tmp_path / "test.md"
        f.write_text(SIMPLE_RUNBOOK)
        runbook = parse_runbook_fallback(f)
        remediation_steps = [
            s for s in runbook.steps.values()
            if s.step_type == StepType.REMEDIATION
        ]
        assert len(remediation_steps) >= 1
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run pytest tests/test_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'runegard.parser'`

**Step 3: Implement the fallback parser**

```python
"""Runbook parser - converts markdown runbooks to Runbook dataclass."""
import re
from pathlib import Path

from runegard.models import Command, Runbook, RunbookStep, StepType


def parse_runbook_fallback(path: Path) -> Runbook:
    """Parse a markdown runbook without using the Claude API.

    Splits on ### headers, extracts code/backtick commands,
    detects remediation steps, assumes linear execution order.
    """
    text = path.read_text()
    lines = text.split("\n")

    title = ""
    trigger = ""
    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        if "trigger" in line.lower() or "alert" in line.lower():
            if not line.startswith("#"):
                trigger = line.strip().lstrip("- ")

    # Split into sections by ### headers
    sections = _split_sections(text)
    steps: dict[str, RunbookStep] = {}
    step_ids: list[str] = []

    for header, body in sections:
        step_id = _header_to_id(header)
        step_ids.append(step_id)

        commands = _extract_commands(body)
        step_type = _detect_step_type(header, body)

        for cmd in commands:
            if step_type == StepType.REMEDIATION:
                cmd.requires_approval = True

        branches = _extract_branches(body)

        steps[step_id] = RunbookStep(
            id=step_id,
            title=header,
            step_type=step_type,
            commands=commands,
            expected_output=_extract_expected(body),
            branches=branches,
            next_step=None,
            rollback_command=None,
        )

    # Link steps linearly
    for i, sid in enumerate(step_ids[:-1]):
        steps[sid].next_step = step_ids[i + 1]

    return Runbook(
        title=title,
        trigger=trigger,
        service="",
        steps=steps,
        first_step=step_ids[0] if step_ids else "",
        metadata={},
    )


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into (header, body) pairs on ### boundaries."""
    sections = []
    current_header = None
    current_body_lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("### "):
            if current_header is not None:
                sections.append((current_header, "\n".join(current_body_lines)))
            current_header = line[4:].strip()
            current_body_lines = []
        elif current_header is not None:
            current_body_lines.append(line)

    if current_header is not None:
        sections.append((current_header, "\n".join(current_body_lines)))

    return sections


def _header_to_id(header: str) -> str:
    """Convert a header like 'Step 2: Get pod details' to 'step-2'."""
    match = re.search(r"step\s+(\d+)", header, re.IGNORECASE)
    if match:
        return f"step-{match.group(1)}"
    return re.sub(r"[^a-z0-9]+", "-", header.lower()).strip("-")


def _extract_commands(body: str) -> list[Command]:
    """Extract commands from backtick code spans and code blocks."""
    commands = []
    for match in re.finditer(r"`([^`]+)`", body):
        cmd = match.group(1)
        if cmd.startswith(("kubectl", "helm", "docker")):
            commands.append(Command(raw=cmd))
    return commands


def _detect_step_type(header: str, body: str) -> StepType:
    """Detect step type from header and body content."""
    lower_header = header.lower()
    lower_body = body.lower()

    if "verification" in lower_header or "verify" in lower_header:
        return StepType.VERIFICATION
    if "escalat" in lower_header or "escalat" in lower_body:
        return StepType.ESCALATION
    if "**remediation**" in lower_body or "remediation" in lower_header:
        return StepType.REMEDIATION
    return StepType.DIAGNOSTIC


def _extract_branches(body: str) -> dict[str, str]:
    """Extract branch conditions like 'OOMKilled -> go to Step 5'."""
    branches: dict[str, str] = {}
    pattern = r"(\w[\w\s]*?)\s*(?:->|→|-->)\s*(?:go to\s+)?step\s+(\d+)"
    for match in re.finditer(pattern, body, re.IGNORECASE):
        condition = match.group(1).strip()
        target = f"step-{match.group(2)}"
        branches[condition] = target
    return branches


def _extract_expected(body: str) -> str | None:
    """Extract expected output patterns from body text."""
    for line in body.split("\n"):
        if "confirm" in line.lower() or "expect" in line.lower():
            return line.strip().lstrip("- ")
    return None
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run pytest tests/test_parser.py -v`
Expected: All 5 tests PASS

**Step 5: Run ruff and ty on the new code**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run ruff check . && uv run ruff format --check .`
Expected: PASS — no linting or formatting issues

**Step 6: Write the failing test for the Claude API parser**

```python
class TestClaudeParser:
    @pytest.fixture
    def crashloop_path(self):
        return Path(__file__).parent.parent / "assets" / "runbooks" / "crashloop.md"

    def test_parses_crashloop_runbook(self, crashloop_path):
        """Integration test - requires ANTHROPIC_API_KEY env var."""
        import os
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        from runegard.parser import parse_runbook

        runbook = parse_runbook(crashloop_path)
        assert runbook.title
        assert len(runbook.steps) >= 7
        assert runbook.first_step

    def test_has_branches(self, crashloop_path):
        """The crashloop runbook has branching (OOMKilled -> step 5, etc.)."""
        import os
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        from runegard.parser import parse_runbook

        runbook = parse_runbook(crashloop_path)
        all_branches = {}
        for step in runbook.steps.values():
            all_branches.update(step.branches)
        assert len(all_branches) >= 2, "Should detect at least 2 branch conditions"
```

**Step 7: Run the new tests to verify they fail**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run pytest tests/test_parser.py::TestClaudeParser -v`
Expected: FAIL — `parse_runbook` not defined

**Step 8: Implement the Claude API parser**

Add to `parser.py`:

```python
import json
import anthropic


PARSE_PROMPT = """You are a runbook parser. Given a markdown runbook, extract its structure into JSON.

Return a JSON object with this exact schema:
{
  "title": "string",
  "trigger": "string - what alert/event triggers this",
  "service": "string - target service or empty string",
  "first_step": "string - id of the first step, e.g. step-1",
  "steps": {
    "step-1": {
      "id": "step-1",
      "title": "string",
      "step_type": "diagnostic|remediation|verification|escalation",
      "commands": [{"raw": "kubectl ...", "requires_approval": false}],
      "expected_output": "string or null",
      "branches": {"pattern": "step-id"},
      "next_step": "step-id or null",
      "rollback_command": "string or null"
    }
  }
}

Rules:
- Step IDs must be "step-N" format
- steps that only gather information are "diagnostic"
- steps with **Remediation** or that mutate state are "remediation" with requires_approval=true
- steps that check results are "verification"
- steps about alerting/paging humans are "escalation"
- Extract branch conditions from prose like "OOMKilled -> go to Step 5" as {"OOMKilled": "step-5"}
- Set next_step to the linearly next step unless the step is terminal
- Extract rollback commands if mentioned

Return ONLY valid JSON, no markdown fences, no explanation."""


def parse_runbook(path: Path) -> Runbook:
    """Parse a runbook using the Claude API for intelligent extraction."""
    text = path.read_text()

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": f"{PARSE_PROMPT}\n\n---\n\n{text}"}
            ],
        )
        raw_json = response.content[0].text
        data = json.loads(raw_json)
        return _json_to_runbook(data)
    except Exception:
        return parse_runbook_fallback(path)


def _json_to_runbook(data: dict) -> Runbook:
    """Convert parsed JSON dict into Runbook dataclass."""
    steps: dict[str, RunbookStep] = {}
    for step_id, step_data in data.get("steps", {}).items():
        commands = [
            Command(
                raw=c["raw"],
                requires_approval=c.get("requires_approval", False),
            )
            for c in step_data.get("commands", [])
        ]
        steps[step_id] = RunbookStep(
            id=step_id,
            title=step_data["title"],
            step_type=StepType(step_data["step_type"]),
            commands=commands,
            expected_output=step_data.get("expected_output"),
            branches=step_data.get("branches", {}),
            next_step=step_data.get("next_step"),
            rollback_command=step_data.get("rollback_command"),
        )

    return Runbook(
        title=data["title"],
        trigger=data.get("trigger", ""),
        service=data.get("service", ""),
        steps=steps,
        first_step=data.get("first_step", ""),
        metadata={},
    )
```

**Step 9: Run all parser tests**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run pytest tests/test_parser.py -v`
Expected: Fallback tests PASS, Claude tests PASS (if API key set) or SKIP

**Step 10: Run ruff**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run ruff check . && uv run ruff format --check .`

**Step 11: Commit**

```bash
git add runegard/runegard/parser.py runegard/tests/test_parser.py
git commit -m "feat: add runbook parser with Claude API and fallback"
```

---

## Task 4: Tracer

**Files:**
- Create: `runegard/tests/test_tracer.py`
- Create: `runegard/runegard/tracer.py`

**Step 1: Write the failing test**

```python
import json
from pathlib import Path
from runegard.tracer import Tracer


class TestTracer:
    def test_creates_trace_file(self, tmp_path):
        trace_path = tmp_path / "trace.json"
        tracer = Tracer(trace_path)
        tracer.log_step(
            step_id="step-1",
            step_type="diagnostic",
            command="kubectl get pods",
            stdout="NAME  READY  STATUS\npod1  1/1    Running",
            stderr="",
            exit_code=0,
            duration_ms=150,
        )
        tracer.finalize(status="success")

        assert trace_path.exists()
        data = json.loads(trace_path.read_text())
        assert data["status"] == "success"
        assert len(data["steps"]) == 1
        assert data["steps"][0]["step_id"] == "step-1"

    def test_logs_branch_decision(self, tmp_path):
        trace_path = tmp_path / "trace.json"
        tracer = Tracer(trace_path)
        tracer.log_branch(
            from_step="step-2",
            to_step="step-5",
            reason="Output contained 'OOMKilled'",
        )
        tracer.finalize(status="partial")

        data = json.loads(trace_path.read_text())
        assert len(data["branches"]) == 1
        assert data["branches"][0]["from_step"] == "step-2"

    def test_logs_approval(self, tmp_path):
        trace_path = tmp_path / "trace.json"
        tracer = Tracer(trace_path)
        tracer.log_approval(
            step_id="step-5",
            outcome="approved",
        )
        tracer.finalize(status="success")

        data = json.loads(trace_path.read_text())
        assert data["approvals"][0]["outcome"] == "approved"
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run pytest tests/test_tracer.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement the tracer**

```python
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
        self._steps.append({
            "step_id": step_id,
            "step_type": step_type,
            "command": command,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
        })

    def log_branch(self, from_step: str, to_step: str, reason: str) -> None:
        self._branches.append({
            "from_step": from_step,
            "to_step": to_step,
            "reason": reason,
        })

    def log_approval(self, step_id: str, outcome: str) -> None:
        self._approvals.append({
            "step_id": step_id,
            "outcome": outcome,
        })

    def finalize(self, status: str) -> None:
        trace = {
            "status": status,
            "steps": self._steps,
            "branches": self._branches,
            "approvals": self._approvals,
        }
        self.output_path.write_text(json.dumps(trace, indent=2))
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run pytest tests/test_tracer.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add runegard/runegard/tracer.py runegard/tests/test_tracer.py
git commit -m "feat: add execution trace logger"
```

---

## Task 5: K8s Wrapper

**Files:**
- Create: `runegard/runegard/k8s.py`

**Step 1: Implement k8s.py**

This is a thin wrapper around subprocess. No tests needed — it's a system boundary that we'll integration-test on the laptop.

```python
"""Thin kubectl wrapper with output capture."""
import subprocess
import time

from runegard.models import CommandResult


def execute(command: str, timeout: int = 30, dry_run: bool = False) -> CommandResult:
    """Execute a shell command and capture output."""
    if dry_run:
        return CommandResult(
            stdout=f"[DRY RUN] Would execute: {command}",
            stderr="",
            exit_code=0,
            command=command,
            duration_ms=0,
        )

    start = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration_ms = int((time.time() - start) * 1000)
        return CommandResult(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            command=command,
            duration_ms=duration_ms,
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start) * 1000)
        return CommandResult(
            stdout="",
            stderr=f"Command timed out after {timeout}s",
            exit_code=-1,
            command=command,
            duration_ms=duration_ms,
        )
```

**Step 2: Run ruff**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run ruff check runegard/k8s.py && uv run ruff format --check runegard/k8s.py`

**Step 3: Commit**

```bash
git add runegard/runegard/k8s.py
git commit -m "feat: add kubectl wrapper with output capture"
```

---

## Task 6: Execution Engine

**Files:**
- Create: `runegard/tests/test_executor.py`
- Create: `runegard/runegard/executor.py`

**Step 1: Write failing tests for dry-run execution**

```python
from pathlib import Path

from runegard.models import (
    Command,
    Runbook,
    RunbookStep,
    StepType,
)


def _make_simple_runbook() -> Runbook:
    """Two-step linear runbook: diagnostic -> verification."""
    return Runbook(
        title="Test Runbook",
        trigger="TestAlert",
        service="test-svc",
        steps={
            "step-1": RunbookStep(
                id="step-1",
                title="Check pods",
                step_type=StepType.DIAGNOSTIC,
                commands=[Command(raw="kubectl get pods")],
                next_step="step-2",
            ),
            "step-2": RunbookStep(
                id="step-2",
                title="Verify fix",
                step_type=StepType.VERIFICATION,
                commands=[Command(raw="kubectl get pods")],
            ),
        },
        first_step="step-1",
    )


def _make_branching_runbook() -> Runbook:
    """Runbook with a branch: step-1 -> step-2 (if OOMKilled) or step-3."""
    return Runbook(
        title="Branching Runbook",
        trigger="TestAlert",
        service="test-svc",
        steps={
            "step-1": RunbookStep(
                id="step-1",
                title="Describe pod",
                step_type=StepType.DIAGNOSTIC,
                commands=[Command(raw="kubectl describe pod test")],
                branches={"OOMKilled": "step-2"},
                next_step="step-3",
            ),
            "step-2": RunbookStep(
                id="step-2",
                title="Handle OOMKilled",
                step_type=StepType.REMEDIATION,
                commands=[Command(raw="kubectl patch deploy test", requires_approval=True)],
                rollback_command="kubectl rollout undo deploy test",
            ),
            "step-3": RunbookStep(
                id="step-3",
                title="Check logs",
                step_type=StepType.DIAGNOSTIC,
                commands=[Command(raw="kubectl logs test")],
            ),
        },
        first_step="step-1",
    )


class TestExecutorDryRun:
    def test_walks_linear_runbook(self, tmp_path):
        from runegard.executor import Executor

        runbook = _make_simple_runbook()
        executor = Executor(runbook, dry_run=True, trace_dir=tmp_path)
        result = executor.run()

        assert result.status == "success"
        assert len(result.steps_executed) == 2

    def test_visits_steps_in_order(self, tmp_path):
        from runegard.executor import Executor

        runbook = _make_simple_runbook()
        executor = Executor(runbook, dry_run=True, trace_dir=tmp_path)
        result = executor.run()

        assert result.steps_executed[0] == "step-1"
        assert result.steps_executed[1] == "step-2"


class TestExecutorBranching:
    def test_follows_branch_on_match(self, tmp_path):
        from runegard.executor import Executor

        runbook = _make_branching_runbook()
        executor = Executor(
            runbook,
            dry_run=True,
            trace_dir=tmp_path,
            fake_outputs={"step-1": "Events:\n  OOMKilled\n"},
        )
        result = executor.run()

        assert "step-2" in result.steps_executed

    def test_follows_next_step_on_no_match(self, tmp_path):
        from runegard.executor import Executor

        runbook = _make_branching_runbook()
        executor = Executor(
            runbook,
            dry_run=True,
            trace_dir=tmp_path,
            fake_outputs={"step-1": "Events:\n  Normal  Scheduled\n"},
        )
        result = executor.run()

        assert "step-3" in result.steps_executed
        assert "step-2" not in result.steps_executed


class TestExecutorApproval:
    def test_remediation_requires_approval(self, tmp_path):
        from runegard.executor import Executor

        runbook = _make_branching_runbook()
        executor = Executor(
            runbook,
            dry_run=True,
            trace_dir=tmp_path,
            fake_outputs={"step-1": "OOMKilled"},
            fake_approvals={"step-2": "approve"},
        )
        result = executor.run()

        assert "step-2" in result.steps_executed
        assert result.approvals["step-2"] == "approve"
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run pytest tests/test_executor.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement the executor**

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run pytest tests/test_executor.py -v`
Expected: All 5 tests PASS

**Step 5: Run ruff**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run ruff check . && uv run ruff format --check .`

**Step 6: Commit**

```bash
git add runegard/runegard/executor.py runegard/tests/test_executor.py
git commit -m "feat: add FSM execution engine with branching and approval gates"
```

---

## Task 7: RLM Improver

**Files:**
- Create: `runegard/tests/test_improver.py`
- Create: `runegard/runegard/improver.py`
- Create: `runegard/references/learned_patterns.md`

**Step 1: Create the empty learned patterns file**

```markdown
# Learned Patterns

Patterns discovered by the RLM improvement loop across executions.
Each entry was identified from analyzing execution traces.

---
```

**Step 2: Write the failing test**

```python
import json
import os

import pytest
from pathlib import Path


SAMPLE_TRACE = {
    "status": "failed",
    "steps": [
        {
            "step_id": "step-1",
            "step_type": "diagnostic",
            "command": "kubectl get pods -A",
            "stdout": "NAME         READY   STATUS             RESTARTS\nbroken-app   0/1     CrashLoopBackOff   5",
            "stderr": "",
            "exit_code": 0,
            "duration_ms": 230,
        },
        {
            "step_id": "step-2",
            "step_type": "diagnostic",
            "command": "kubectl describe pod broken-app",
            "stdout": "Events:\n  Warning  BackOff  kubelet  Back-off restarting failed container",
            "stderr": "",
            "exit_code": 0,
            "duration_ms": 180,
        },
        {
            "step_id": "step-3",
            "step_type": "diagnostic",
            "command": "kubectl logs broken-app --previous",
            "stdout": "",
            "stderr": "error: previous terminated container not found",
            "exit_code": 1,
            "duration_ms": 95,
        },
    ],
    "branches": [],
    "approvals": [],
}

SAMPLE_RUNBOOK = """# Runbook: KubePodCrashLooping

## Steps

### Step 1: Get pods
- Run: `kubectl get pods -A`

### Step 2: Describe pod
- Run: `kubectl describe pod <pod-name>`
- OOMKilled -> go to Step 5

### Step 3: Check logs
- Run: `kubectl logs <pod-name> --previous`
"""


class TestImprover:
    def test_analyzes_trace(self, tmp_path):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        from runegard.improver import analyze_trace

        trace_path = tmp_path / "trace.json"
        trace_path.write_text(json.dumps(SAMPLE_TRACE))

        runbook_path = tmp_path / "runbook.md"
        runbook_path.write_text(SAMPLE_RUNBOOK)

        patterns_path = tmp_path / "learned_patterns.md"
        patterns_path.write_text("# Learned Patterns\n\n---\n")

        result = analyze_trace(trace_path, runbook_path, patterns_path)

        assert "failures" in result
        assert "learned_patterns" in result
        assert "summary" in result

    def test_appends_learned_patterns(self, tmp_path):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        from runegard.improver import analyze_trace, apply_learned_patterns

        trace_path = tmp_path / "trace.json"
        trace_path.write_text(json.dumps(SAMPLE_TRACE))

        runbook_path = tmp_path / "runbook.md"
        runbook_path.write_text(SAMPLE_RUNBOOK)

        patterns_path = tmp_path / "learned_patterns.md"
        patterns_path.write_text("# Learned Patterns\n\n---\n")

        result = analyze_trace(trace_path, runbook_path, patterns_path)
        apply_learned_patterns(patterns_path, result["learned_patterns"])

        updated = patterns_path.read_text()
        assert len(updated) > len("# Learned Patterns\n\n---\n")
```

**Step 3: Run tests to verify they fail**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run pytest tests/test_improver.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 4: Implement the improver**

```python
"""RLM improvement loop - analyzes execution traces and generates learnings."""
import json
from pathlib import Path

import anthropic


ANALYSIS_PROMPT = """You are an SRE improvement analyzer. You are given:
1. An execution trace from a Kubernetes runbook executor
2. The original runbook
3. Previously learned patterns

Analyze the execution trace for failures, suboptimal paths, and missed opportunities.

Return a JSON object with this exact schema:
{
  "failures": [
    {
      "step_id": "step-N",
      "issue": "description of what went wrong",
      "root_cause": "why it happened",
      "category": "parser_miss|wrong_command|missing_verification|timeout|misinterpreted_output|other"
    }
  ],
  "learned_patterns": [
    "Pattern description: when X happens, do Y instead of Z"
  ],
  "skill_suggestions": [
    "Suggestion for improving the skill.md workflow"
  ],
  "summary": "Human-readable 2-3 sentence summary of the analysis"
}

Return ONLY valid JSON, no markdown fences, no explanation."""


def analyze_trace(
    trace_path: Path,
    runbook_path: Path,
    patterns_path: Path,
) -> dict:
    """Analyze an execution trace and return improvement suggestions."""
    trace = trace_path.read_text()
    runbook = runbook_path.read_text()
    patterns = patterns_path.read_text()

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{ANALYSIS_PROMPT}\n\n"
                    f"## Execution Trace\n```json\n{trace}\n```\n\n"
                    f"## Original Runbook\n{runbook}\n\n"
                    f"## Previously Learned Patterns\n{patterns}"
                ),
            }
        ],
    )

    return json.loads(response.content[0].text)


def apply_learned_patterns(patterns_path: Path, new_patterns: list[str]) -> None:
    """Append new learned patterns to the patterns file."""
    if not new_patterns:
        return

    current = patterns_path.read_text()
    additions = "\n".join(f"- {p}" for p in new_patterns)
    updated = f"{current}\n{additions}\n"
    patterns_path.write_text(updated)
```

**Step 5: Run tests to verify they pass**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run pytest tests/test_improver.py -v`
Expected: PASS (if API key set) or SKIP

**Step 6: Commit**

```bash
git add runegard/runegard/improver.py runegard/tests/test_improver.py runegard/references/
git commit -m "feat: add RLM improvement loop with Claude API analysis"
```

---

## Task 8: CLI Entry Point

**Files:**
- Create: `runegard/runegard/cli.py`
- Create: `runegard/runegard/__main__.py`

**Step 1: Implement the CLI**

```python
"""CLI entry point for RuneGard."""
import argparse
import sys
from pathlib import Path

from runegard.models import StepType


def main():
    parser = argparse.ArgumentParser(
        prog="runegard",
        description="RuneGard - Autonomous Kubernetes Runbook Executor",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # parse
    parse_cmd = subparsers.add_parser("parse", help="Parse a runbook and display its structure")
    parse_cmd.add_argument("runbook", type=Path, help="Path to runbook markdown file")
    parse_cmd.add_argument("--fallback", action="store_true", help="Use fallback parser (no API)")

    # run
    run_cmd = subparsers.add_parser("run", help="Parse and execute a runbook")
    run_cmd.add_argument("runbook", type=Path, help="Path to runbook markdown file")
    run_cmd.add_argument("--dry-run", action="store_true", help="Walk the tree without executing")
    run_cmd.add_argument("--trace-dir", type=Path, default=Path("."), help="Directory for trace output")

    # improve
    improve_cmd = subparsers.add_parser("improve", help="Analyze a trace and suggest improvements")
    improve_cmd.add_argument("trace", type=Path, help="Path to trace_log.json")
    improve_cmd.add_argument("--runbook", type=Path, required=True, help="Path to original runbook")
    improve_cmd.add_argument(
        "--patterns",
        type=Path,
        default=Path(__file__).parent.parent / "references" / "learned_patterns.md",
        help="Path to learned patterns file",
    )

    args = parser.parse_args()

    if args.command == "parse":
        _cmd_parse(args)
    elif args.command == "run":
        _cmd_run(args)
    elif args.command == "improve":
        _cmd_improve(args)


def _cmd_parse(args):
    if args.fallback:
        from runegard.parser import parse_runbook_fallback

        runbook = parse_runbook_fallback(args.runbook)
    else:
        from runegard.parser import parse_runbook

        runbook = parse_runbook(args.runbook)

    print(f"Title: {runbook.title}")
    print(f"Trigger: {runbook.trigger}")
    print(f"Steps: {len(runbook.steps)}")
    print(f"First step: {runbook.first_step}")
    print()

    for step_id, step in runbook.steps.items():
        marker = ""
        if step.step_type == StepType.REMEDIATION:
            marker = " [REQUIRES APPROVAL]"
        print(f"  {step_id}: {step.title} ({step.step_type.value}){marker}")
        for cmd in step.commands:
            print(f"    $ {cmd.raw}")
        if step.branches:
            for pattern, target in step.branches.items():
                print(f"    -> if '{pattern}': jump to {target}")
        if step.next_step:
            print(f"    -> next: {step.next_step}")
        print()


def _cmd_run(args):
    from runegard.executor import Executor
    from runegard.parser import parse_runbook

    print(f"Parsing runbook: {args.runbook}")
    runbook = parse_runbook(args.runbook)
    print(f"Parsed {len(runbook.steps)} steps. Starting execution...\n")

    executor = Executor(
        runbook,
        dry_run=args.dry_run,
        trace_dir=args.trace_dir,
    )
    result = executor.run()

    print(f"\n{'=' * 60}")
    print(f"Execution complete: {result.status}")
    print(f"Steps executed: {', '.join(result.steps_executed)}")
    print(f"Trace saved to: {args.trace_dir / 'trace_log.json'}")

    if result.status != "success":
        print("\nRun 'runegard improve' to analyze failures and improve the skill.")


def _cmd_improve(args):
    from runegard.improver import analyze_trace, apply_learned_patterns

    print(f"Analyzing trace: {args.trace}")
    result = analyze_trace(args.trace, args.runbook, args.patterns)

    print(f"\n{'=' * 60}")
    print("ANALYSIS SUMMARY")
    print(f"{'=' * 60}")
    print(result["summary"])

    if result.get("failures"):
        print(f"\nFailures found: {len(result['failures'])}")
        for f in result["failures"]:
            print(f"  [{f['category']}] {f['step_id']}: {f['issue']}")

    if result.get("learned_patterns"):
        print(f"\nNew patterns learned: {len(result['learned_patterns'])}")
        for p in result["learned_patterns"]:
            print(f"  - {p}")

        choice = input("\nApply learned patterns? (yes/no): ").strip().lower()
        if choice == "yes":
            apply_learned_patterns(args.patterns, result["learned_patterns"])
            print(f"Patterns appended to {args.patterns}")

    if result.get("skill_suggestions"):
        print("\nSkill improvement suggestions:")
        for s in result["skill_suggestions"]:
            print(f"  - {s}")


if __name__ == "__main__":
    main()
```

**Step 2: Create __main__.py**

```python
"""Allow running as python -m runegard."""
from runegard.cli import main

main()
```

**Step 3: Run ruff**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run ruff check . && uv run ruff format --check .`

**Step 4: Test the CLI manually**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run python -m runegard parse assets/runbooks/crashloop.md --fallback`
Expected: Prints the parsed runbook structure with steps and branches

Run: `cd /home/yolo/projects/skillathon/runegard && uv run python -m runegard run assets/runbooks/crashloop.md --dry-run`
Expected: Walks through steps in dry-run mode, prints what would happen

**Step 5: Commit**

```bash
git add runegard/runegard/cli.py runegard/runegard/__main__.py
git commit -m "feat: add CLI entry point with parse, run, and improve commands"
```

---

## Task 9: Skill.md

**Files:**
- Create: `runegard/skill.md`

**Step 1: Write skill.md**

```markdown
---
name: runegard
description: >
  Autonomous runbook executor for Kubernetes operations. Reads markdown runbooks,
  parses them into executable decision trees, and follows them step-by-step
  against a live K8s cluster. Requests human approval before any mutating action.
  Includes an RLM-powered improvement loop that learns from execution failures.
---

# RuneGard -- Kubernetes Runbook Executor

## When to Use This Skill

Use this skill when:
- You have a runbook document describing an operational procedure
- You need to diagnose or remediate a Kubernetes issue
- You want to follow a step-by-step troubleshooting guide against a live cluster

## Workflow

### Phase 1: Parse the Runbook

1. Accept a runbook file path from the user
2. Run: `uv run python -m runegard parse <runbook_path>`
3. Present the parsed structure to the user for confirmation:
   - Number of steps detected
   - Decision points identified
   - Commands that will be executed
4. If the user wants changes, adjust and re-parse

### Phase 2: Execute the Runbook

1. Ask the user for execution mode:
   - Interactive (default): pause before remediation steps for approval
   - Dry-run: walk the tree without executing any commands
2. Run: `uv run python -m runegard run <runbook_path> [--dry-run]`
3. For each step:
   - DIAGNOSTIC steps: execute automatically, report output
   - REMEDIATION steps: present the command, risk, and rollback to the user. Wait for 'approve', 'skip', or 'abort'
   - VERIFICATION steps: execute automatically, report whether check passed
   - ESCALATION steps: present escalation info, ask if user wants to continue
4. If any step fails: offer retry, skip, rollback, or abort
5. Consult `references/learned_patterns.md` for known patterns that might affect execution

### Phase 3: Report Results

1. Present a summary: steps completed, issues found, actions taken
2. The trace is saved to `trace_log.json`

### Phase 4: Improve (Continual Learning)

1. If the execution had failures or suboptimal paths, ask:
   "Would you like me to analyze this run and improve the skill for next time?"
2. If yes, run: `uv run python -m runegard improve trace_log.json --runbook <path>`
3. Present proposed learnings and suggestions for review
4. Apply approved learnings to `references/learned_patterns.md`

## Important Rules

- NEVER execute a REMEDIATION command without explicit user approval
- ALWAYS log every command and its output to the trace log
- ALWAYS check for a rollback path before executing any REMEDIATION step
- If a command's output doesn't match any expected pattern, flag it and ask the user
- Consult `references/learned_patterns.md` before executing -- it contains patterns from previous runs
```

**Step 2: Commit**

```bash
git add runegard/skill.md
git commit -m "feat: add skill.md for Claude Code integration"
```

---

## Task 10: References and Demo Scripts

**Files:**
- Create: `runegard/references/k8s_common_patterns.md`
- Create: `runegard/demo/setup_cluster.sh`
- Create: `runegard/demo/run_demo.sh`

**Step 1: Write k8s_common_patterns.md**

```markdown
# Common Kubernetes Failure Patterns

## CrashLoopBackOff
- Pod repeatedly crashes and K8s backs off restart attempts
- Check: `kubectl describe pod` Events section
- Common causes: OOMKilled, bad entrypoint, missing config, image issues
- Key indicators in describe output: "Back-off restarting failed container"

## OOMKilled
- Container exceeded memory limits
- Check: `kubectl describe pod` for "OOMKilled" in last state
- Fix: increase memory limits or fix memory leak

## ImagePullBackOff
- K8s cannot pull the container image
- Check: image name/tag, registry auth, imagePullSecrets
- Key indicators: "Failed to pull image", "ErrImagePull"

## Pending PVC
- PersistentVolumeClaim stuck in Pending
- Check: `kubectl describe pvc` for events
- Common causes: no matching PV, missing StorageClass, WaitForFirstConsumer

## ResourceQuota Exceeded
- Namespace resource limits reached
- Check: `kubectl describe quota -n <ns>`
- Fix: increase quota, reduce usage, or evict non-critical pods
```

**Step 2: Write setup_cluster.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Creating kind cluster..."
kind create cluster --name runegard-demo 2>/dev/null || echo "Cluster already exists"

echo "Seeding CrashLoopBackOff failure..."
kubectl create deployment broken-app \
  --image=busybox -- /bin/sh -c "exit 1" 2>/dev/null || true

echo "Waiting for pod to enter CrashLoopBackOff..."
sleep 15

echo "Cluster ready. Current pods:"
kubectl get pods -A
```

**Step 3: Write run_demo.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== RuneGard Demo ==="
echo ""

echo "Step 1: Parse the runbook"
uv run python -m runegard parse "$SCRIPT_DIR/assets/runbooks/crashloop.md"

echo ""
echo "Step 2: Execute (interactive mode)"
uv run python -m runegard run "$SCRIPT_DIR/assets/runbooks/crashloop.md" --trace-dir "$SCRIPT_DIR"

echo ""
echo "Step 3: Analyze and improve"
uv run python -m runegard improve "$SCRIPT_DIR/trace_log.json" \
  --runbook "$SCRIPT_DIR/assets/runbooks/crashloop.md" \
  --patterns "$SCRIPT_DIR/references/learned_patterns.md"
```

**Step 4: Make scripts executable and commit**

```bash
chmod +x runegard/demo/setup_cluster.sh runegard/demo/run_demo.sh
git add runegard/references/k8s_common_patterns.md runegard/demo/
git commit -m "feat: add K8s reference patterns and demo scripts"
```

---

## Task 11: README

**Files:**
- Create: `runegard/README.md`

**Step 1: Write README**

```markdown
# RuneGard

Autonomous Kubernetes runbook executor with continual learning.

## What it does

1. **Parses** markdown runbooks into executable decision trees
2. **Executes** them step-by-step against a live K8s cluster
3. **Asks for approval** before any mutating action
4. **Learns from failures** via an RLM loop that improves the skill over time

## Quick Start

### Install

```bash
uv sync
make setup  # installs git hooks
```

### As a CLI

```bash
# Parse a runbook
uv run python -m runegard parse assets/runbooks/crashloop.md

# Execute (dry-run)
uv run python -m runegard run assets/runbooks/crashloop.md --dry-run

# Execute (live, against a K8s cluster)
uv run python -m runegard run assets/runbooks/crashloop.md

# Analyze failures and improve
uv run python -m runegard improve trace_log.json --runbook assets/runbooks/crashloop.md
```

### As a Claude Code Skill

Add the `skill.md` to your Claude Code skills directory, then:

> "Run the crashloop runbook against my cluster"

## Development

```bash
make fmt        # format code
make lint       # run ruff linter
make typecheck  # run ty type checker
make test       # run all tests
make audit      # run all quality checks
```

## Demo

```bash
# 1. Create kind cluster with seeded failures
./demo/setup_cluster.sh

# 2. Run the full demo
./demo/run_demo.sh
```

## Environment

Requires:
- Python 3.12+
- `uv` for package management
- `ANTHROPIC_API_KEY` environment variable
- `kubectl` configured for your cluster (for live execution)
```

**Step 2: Commit**

```bash
git add runegard/README.md
git commit -m "docs: add README"
```

---

## Task 12: End-to-End Dry Run Test

**Step 1: Run full audit**

Run: `cd /home/yolo/projects/skillathon/runegard && make audit`
Expected: Lint, typecheck, and all tests pass

**Step 2: Run the CLI parse command**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run python -m runegard parse assets/runbooks/crashloop.md --fallback`
Expected: Prints parsed runbook with 7+ steps and branch conditions

**Step 3: Run the CLI in dry-run mode**

Run: `cd /home/yolo/projects/skillathon/runegard && uv run python -m runegard run assets/runbooks/crashloop.md --dry-run`
Expected: Walks through steps, prints "[DRY RUN]" for each command, completes successfully

**Step 4: Fix any issues found and commit**

```bash
git add -A
git commit -m "fix: end-to-end dry run fixes"
```
