"""RLM improvement loop - analyzes execution traces and generates learnings."""

import json
from pathlib import Path

import anthropic

ANALYSIS_PROMPT = """\
You are an SRE improvement analyzer. You are given:
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
      "category": "parser_miss|wrong_command|missing_verification|timeout|other"
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
