# RuneGärd

Autonomous Kubernetes runbook executor with continual learning.

## What it does

1. **Parses** markdown runbooks into executable decision trees
2. **Executes** them step-by-step against a live K8s cluster
3. **Asks for approval** before any mutating action
4. **Learns from failures** via an CL loop that improves the skill over time

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
