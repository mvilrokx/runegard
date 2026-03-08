import os
from pathlib import Path

import pytest

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
            s for s in runbook.steps.values() if s.step_type == StepType.REMEDIATION
        ]
        assert len(remediation_steps) >= 1


class TestClaudeParser:
    @pytest.fixture
    def crashloop_path(self):
        return Path(__file__).parent.parent / "assets" / "runbooks" / "crashloop.md"

    def test_parses_crashloop_runbook(self, crashloop_path):
        """Integration test - requires ANTHROPIC_API_KEY env var."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        from runegard.parser import parse_runbook

        runbook = parse_runbook(crashloop_path)
        assert runbook.title
        assert len(runbook.steps) >= 7
        assert runbook.first_step

    def test_has_branches(self, crashloop_path):
        """The crashloop runbook has branching (OOMKilled -> step 5, etc.)."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        from runegard.parser import parse_runbook

        runbook = parse_runbook(crashloop_path)
        all_branches = {}
        for step in runbook.steps.values():
            all_branches.update(step.branches)
        assert len(all_branches) >= 2, "Should detect at least 2 branch conditions"
