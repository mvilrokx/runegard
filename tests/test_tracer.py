import json

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
