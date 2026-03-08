import json
import os

import pytest

SAMPLE_TRACE = {
    "status": "failed",
    "steps": [
        {
            "step_id": "step-1",
            "step_type": "diagnostic",
            "command": "kubectl get pods -A",
            "stdout": "NAME         READY   STATUS             RESTARTS\n"
            "broken-app   0/1     CrashLoopBackOff   5",
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
