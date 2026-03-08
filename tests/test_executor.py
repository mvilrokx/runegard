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
            fake_approvals={"step-2": "approve"},
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
