# RuneGard Design Document

> Refined design for the RuneGard autonomous runbook executor skill.
> Based on `runegard-spec.md` with scope adjustments for hackathon feasibility.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Priority | Execution engine + RLM loop | These are the demo differentiators |
| Parser scope | Markdown-only (v1) | Covers demo runbooks; extensible later |
| Dev environment | VPS for code, laptop for K8s demo | No Docker/kind needed during development |
| RLM implementation | Python script calling Claude API | Direct control, no third-party RLM library |
| Packaging | Python CLI + skill.md wrapper | Works standalone and inside Claude Code |
| Approval gate | Simple text prompts | No `rich` dependency, time saved for core logic |
| Demo runbooks | CrashLoopBackOff primary, QuotaExceeded stretch | Focus over breadth |
| What RLM patches | skill.md + learned_patterns.md | No auto-patching Python code (too risky for demo) |

---

## Project Structure

```
runegard/
├── skill.md                          # Claude Code skill definition
├── runegard/
│   ├── __init__.py
│   ├── cli.py                        # Entry point: python -m runegard
│   ├── parser.py                     # Markdown runbook -> Runbook dataclass
│   ├── executor.py                   # FSM execution engine + approval gate
│   ├── k8s.py                        # kubectl wrapper with output capture
│   ├── tracer.py                     # Execution trace logger (append-only JSON)
│   └── improver.py                   # RLM loop: trace -> Claude API -> patches
├── references/
│   ├── k8s_common_patterns.md        # Common K8s failure signatures
│   └── learned_patterns.md           # RLM-generated learnings (grows over time)
├── assets/
│   └── runbooks/
│       ├── crashloop.md              # Demo: KubePodCrashLooping
│       └── quota_exceeded.md         # Stretch: KubeQuotaExceeded
├── demo/
│   ├── setup_cluster.sh              # Create kind cluster + seed failures
│   └── run_demo.sh                   # End-to-end demo script
├── tests/
│   ├── test_parser.py
│   ├── test_executor.py
│   └── test_improver.py
├── pyproject.toml                    # Dependencies: anthropic, pyyaml
└── README.md
```

---

## Data Model

```python
from dataclasses import dataclass
from enum import Enum

class StepType(Enum):
    DIAGNOSTIC = "diagnostic"          # auto-run, gather info
    REMEDIATION = "remediation"        # requires approval
    VERIFICATION = "verification"      # auto-run, check result
    ESCALATION = "escalation"          # inform user, offer handoff

@dataclass
class Command:
    raw: str                           # e.g., "kubectl get pods -A"
    requires_approval: bool            # True if this mutates state

@dataclass
class RunbookStep:
    id: str                            # e.g., "step-2"
    title: str                         # "Get pod details"
    step_type: StepType                # DIAGNOSTIC | REMEDIATION | VERIFICATION | ESCALATION
    commands: list[Command]
    expected_output: str | None        # what success looks like
    branches: dict[str, str]           # condition_pattern -> next step_id
    next_step: str | None              # default next step if no branch matches
    rollback_command: str | None       # command to undo this step

@dataclass
class Runbook:
    title: str
    trigger: str                       # what alert triggers this
    service: str
    steps: dict[str, RunbookStep]      # step_id -> step
    first_step: str                    # entry point step_id
    metadata: dict                     # any extra frontmatter
```

---

## Parser (`parser.py`)

**Input:** Markdown file path.

**Primary strategy:** Send markdown to Claude API with a structured prompt requesting JSON output matching the Runbook schema. Claude handles natural language conditions, branch detection, and step type classification.

**Fallback:** If API call fails, do a basic structural parse — split on `###` headers, extract code blocks as commands, assume linear execution order.

**Cost:** ~1K tokens in, ~2K tokens out per runbook. Negligible.

---

## Execution Engine (`executor.py`)

Walks the parsed Runbook as an FSM:

```
START -> get first_step -> execute step -> evaluate output -> choose next step -> repeat -> DONE
```

### Per-step behavior

| StepType | Auto-execute? | Approval? | On failure |
|----------|:---:|:---:|---|
| DIAGNOSTIC | Yes | No | Log warning, continue |
| REMEDIATION | No | Yes | Offer: retry / skip / rollback / abort |
| VERIFICATION | Yes | No | Flag failed, ask user |
| ESCALATION | No | N/A | Present info, ask: continue or hand off? |

### Branching

After each step, compare command stdout against `branches` patterns (substring match). If a pattern matches, jump to that step. Otherwise follow `next_step`. If neither exists, execution is complete.

### Approval flow (REMEDIATION steps)

```
APPROVAL REQUIRED -- Step 5: Handle OOMKilled

Command:  kubectl patch deployment broken-app ...
Rollback: kubectl patch deployment broken-app ... (revert)

Type 'approve', 'skip', or 'abort':
```

### Execution context

Maintained in memory: current step, visited steps, collected outputs (step_id -> stdout). Written to trace log after each step.

### Dry-run mode

Walk the tree, print what would happen, don't call k8s.py. Used for testing on VPS.

---

## RLM Improvement Loop (`improver.py`)

Runs after execution completes, especially on failures.

### Flow

```
trace_log.json -> improver.py -> Claude API -> analysis + patches -> user review -> apply
```

### Trace log contents (written by `tracer.py`)

- Each step: id, type, command, stdout, stderr, exit code, duration
- Branch decisions and reasoning
- Approval gate outcomes
- Final status: success / partial / failed

### Claude API analysis

Receives: full trace + original runbook + current learned_patterns.md

Returns JSON:
- `failures`: identified issues with root cause
- `skill_patches`: suggested edits to skill.md
- `learned_patterns`: new entries for learned_patterns.md
- `summary`: human-readable analysis

### What gets patched

- `learned_patterns.md` — appended with new learnings, consulted on future runs
- `skill.md` — workflow adjustments, presented as diff for user approval

### What does NOT get patched

- Python source code

### Demo story

1. Run runbook -> step fails due to missed edge case
2. Run "improve" -> RLM analyzes, adds pattern to learned_patterns.md
3. Re-run same runbook -> skill consults learned patterns, handles edge case
4. Judges see file grow and behavior change across runs

---

## CLI & Skill Integration

### CLI commands

```
python -m runegard parse <runbook.md>          # Parse and display decision tree
python -m runegard run <runbook.md>             # Parse + execute interactively
python -m runegard run <runbook.md> --dry-run   # Walk tree without executing
python -m runegard improve <trace.json>         # Run RLM analysis on a trace
```

### Skill.md integration

Claude Code invokes the CLI:
1. `parse` — show user the parsed tree for confirmation
2. `run` — execute interactively, relay approval prompts
3. `improve` — analyze trace, present patches

### Environment detection

CLI detects Claude Code vs standalone (env var or TTY check) to adjust output format.

---

## Testing Strategy

All tests run on the VPS without a K8s cluster.

### test_parser.py
- Feed CrashLoopBackOff runbook into parser, assert correct Runbook structure
- Test fallback parser with simple linear runbook
- Requires: Claude API key

### test_executor.py
- Dry-run mode — walks tree, logs actions, never calls kubectl
- Inject fake outputs to test branching (e.g., "OOMKilled" -> step 5)
- Assert approval gate triggers for REMEDIATION steps
- Assert rollback offered on failure
- Requires: nothing

### test_improver.py
- Feed sample trace with deliberate failure into improver
- Assert valid patches and learned patterns returned
- Requires: Claude API key

---

## Dependencies

```
anthropic    # Claude API client
pyyaml       # YAML frontmatter parsing
```

System tools (laptop only): docker, kind, kubectl
