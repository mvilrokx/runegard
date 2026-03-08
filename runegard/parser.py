"""Runbook parser - converts markdown runbooks to Runbook dataclass."""

import json
import re
from pathlib import Path

import anthropic

from runegard.models import Command, Runbook, RunbookStep, StepType

PARSE_PROMPT = """\
You are a runbook parser. Given a markdown runbook, extract its structure as JSON.

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
            messages=[{"role": "user", "content": f"{PARSE_PROMPT}\n\n---\n\n{text}"}],
        )
        raw_json = response.content[0].text  # type: ignore[union-attr]
        data = json.loads(raw_json)
        return _json_to_runbook(data)
    except Exception as e:
        print(f"[warn] Claude API parser failed ({e}), using fallback")
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
        if ("trigger" in line.lower() or "alert" in line.lower()) and not line.startswith("#"):
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
