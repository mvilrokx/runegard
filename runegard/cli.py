"""CLI entry point for RuneGard."""

import argparse
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
    run_cmd.add_argument(
        "--trace-dir", type=Path, default=Path("."), help="Directory for trace output"
    )

    # improve
    improve_cmd = subparsers.add_parser("improve", help="Analyze a trace and suggest improvements")
    improve_cmd.add_argument("trace", type=Path, help="Path to trace_log.json")
    improve_cmd.add_argument(
        "--runbook", type=Path, required=True, help="Path to original runbook"
    )
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
