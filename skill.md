---
name: runegard
description: >
  Autonomous runbook executor for Kubernetes operations. Reads markdown runbooks,
  parses them into executable decision trees, and follows them step-by-step
  against a live K8s cluster. Requests human approval before any mutating action.
  Includes an CL-powered improvement loop that learns from execution failures.
---

# RuneGärd -- Kubernetes Runbook Executor

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
