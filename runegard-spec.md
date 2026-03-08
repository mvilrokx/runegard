# 🛡️ RuneGard — Autonomous Runbook Executor Skill

> **Hackathon:** Skillathon — The First Agent Skills Hackathon (March 2026)
> **Tracks:** Continual Learning + Data
> **Stack:** Python · Claude Code · Claude Opus 4.6 · kind (K8s) · RLM
> **Author:** Mark Vilrokx

---

## 1. Vision (30-Second Pitch)

RuneGard is an agent skill that **reads any operations runbook** — markdown, Confluence wiki, YAML-frontmatter, or plain-text — **parses it into an executable decision tree**, and **follows it step-by-step against a live Kubernetes cluster**, requesting human approval before any mutating action. When the skill fails, an **RLM-powered improvement loop** analyzes the failure trajectory and automatically patches the skill for next time.

**Why it wins:** It combines a practical, demo-friendly use case (SRE automation) with the Continual Learning track's RLM requirement, and it's packaged as a proper `skill.md`-standard skill that judges can install and test in Claude Code.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     RuneGard Skill                       │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐   ┌─────────────┐ │
│  │ Runbook       │    │ Execution    │   │ Tool        │ │
│  │ Parser        │───▶│ Engine       │──▶│ Bridge      │ │
│  │ (multi-format)│    │ (state FSM)  │   │ (kubectl,   │ │
│  └──────────────┘    └──────┬───────┘   │  helm, etc) │ │
│                             │           └─────────────┘ │
│                    ┌────────▼────────┐                   │
│                    │ Approval Gate   │                   │
│                    │ (human-in-loop) │                   │
│                    └─────────────────┘                   │
│                                                          │
│  ┌──────────────────────────────────────────────────────┐│
│  │              RLM Improvement Loop                    ││
│  │  trajectory logs ──▶ RLM analysis ──▶ skill patch   ││
│  └──────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

---

## 3. Runbook Format Support

Runbooks in the wild come in many shapes. RuneGard must handle all common formats without requiring users to convert them first.

### 3.1 Supported Formats

| Format | Source | Detection | Notes |
|--------|--------|-----------|-------|
| **Markdown** | GitHub repos, internal wikis, K8s Mixin alerts | `.md` extension or markdown header patterns | Primary target. Most open-source runbooks use this. |
| **Markdown + YAML frontmatter** | Modern SRE teams, Backstage catalogs | `---` fences at top of file | Frontmatter provides structured metadata (severity, service, alert name, owner, escalation). |
| **Confluence wiki markup** | Enterprise teams on Atlassian stack | Confluence-specific syntax (e.g., `{code}`, `{panel}`, `||header||`) | Convert to intermediate markdown first, then parse. |
| **Plain text / unstructured** | Legacy wikis, Google Docs exports, Notion exports, email threads | No detectable structure markers | Fallback: use the LLM itself to identify steps, conditions, and commands from natural language. |
| **HTML** | Exported Confluence pages, internal portals | `.html` extension or `<html>` tag | Strip to text, then parse as unstructured. |

### 3.2 Runbook Structural Elements to Extract

Regardless of format, the parser must identify these elements:

```python
@dataclass
class RunbookStep:
    id: str                          # e.g., "step-3a"
    title: str                       # human-readable step name
    description: str                 # what this step does and why
    step_type: StepType              # DIAGNOSTIC | REMEDIATION | VERIFICATION | ESCALATION | ROLLBACK
    commands: list[Command]          # shell commands to execute
    expected_output: str | None      # what success looks like
    failure_indicators: list[str]    # patterns that indicate this step failed
    conditions: list[Condition]      # prerequisites / branching conditions
    next_steps: dict[str, str]       # condition_result -> next step_id
    requires_approval: bool          # True for REMEDIATION steps
    rollback_step_id: str | None     # which step undoes this one
    timeout_seconds: int             # max time before marking as failed

@dataclass
class Runbook:
    title: str
    description: str
    trigger: str                     # what alert/event triggers this runbook
    severity: str                    # critical / warning / info
    service: str                     # target service or component
    owner: str                       # team or person responsible
    steps: list[RunbookStep]
    decision_tree: dict              # adjacency list of step transitions
    rollback_plan: list[str]         # ordered list of rollback step IDs
    metadata: dict                   # any extra frontmatter fields
```

### 3.3 Parsing Strategy

1. **Format Detection** — auto-detect format from file extension + content sniffing (first 500 chars)
2. **Normalization** — convert all formats to a canonical intermediate markdown representation
3. **Structural Extraction** — use regex + heuristics for well-structured docs (numbered lists, headers, code blocks)
4. **LLM Fallback** — for unstructured/ambiguous runbooks, call Claude to extract the `Runbook` dataclass fields from the normalized text
5. **Validation** — ensure the decision tree has no orphan steps, every REMEDIATION has a rollback, and all commands are syntactically valid

---

## 4. Execution Engine

### 4.1 State Machine

The execution engine follows the parsed decision tree as a finite state machine:

```
                    ┌──────────┐
                    │  START   │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
              ┌────▶│ EVALUATE │◀───────────────┐
              │     │ CONDITION│                 │
              │     └────┬─────┘                 │
              │          │                       │
              │    ┌─────▼──────┐          ┌─────┴──────┐
              │    │ DIAGNOSTIC │          │ NEXT STEP  │
              │    │ (auto-run) │          │            │
              │    └─────┬──────┘          └────────────┘
              │          │                       ▲
              │    ┌─────▼──────┐                │
              │    │ APPROVAL   │────(denied)────┘
              │    │ GATE       │
              │    └─────┬──────┘
              │          │(approved)
              │    ┌─────▼──────┐
              │    │ REMEDIATE  │
              │    └─────┬──────┘
              │          │
              │    ┌─────▼──────┐
              │    │ VERIFY     │
              │    └─────┬──────┘
              │          │
              │     fail │  success
              │     ┌────┘  └──────▶ NEXT STEP
              │     ▼
              │  ┌──────────┐
              └──│ ROLLBACK  │
                 └──────────┘
```

### 4.2 Execution Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Interactive** (default) | Pause before every REMEDIATION step, show planned command + expected effect, wait for `approve` / `deny` / `skip` | Production use, demo |
| **Dry-Run** | Parse and walk the tree but execute no commands; print what *would* happen | Testing the runbook parser |
| **Auto** | Execute everything without approval gates (DIAGNOSTIC + REMEDIATION) | CI/CD, fully trusted runbooks |

### 4.3 Command Execution

Commands are executed via `subprocess` in the local shell (which has `kubectl` configured for the `kind` cluster). The engine:

1. Captures `stdout`, `stderr`, and exit code
2. Compares output against `expected_output` patterns
3. Checks for `failure_indicators` in stderr
4. Stores all output in the execution trace (for the RLM loop later)
5. If a command times out, marks step as FAILED and triggers rollback evaluation

### 4.4 Approval Gate

When a REMEDIATION step is reached:

```
╔══════════════════════════════════════════════════════════╗
║  🔶 APPROVAL REQUIRED — Step 4: Scale Down Deployment   ║
║                                                          ║
║  Runbook says: "Scale the broken deployment to 0         ║
║  replicas to stop the crash loop, then redeploy."        ║
║                                                          ║
║  Command to execute:                                     ║
║  $ kubectl scale deployment/broken-app --replicas=0      ║
║                                                          ║
║  Risk: LOW — scaling to 0 is non-destructive             ║
║  Rollback: kubectl scale deployment/broken-app           ║
║            --replicas=<previous>                         ║
║                                                          ║
║  [approve]  [deny]  [skip]  [modify command]             ║
╚══════════════════════════════════════════════════════════╝
```

The agent presents this as a structured message. In Claude Code, the user types their choice and the agent continues.

---

## 5. Tool Bridge

The skill needs access to CLI tools. These are exposed as skill scripts:

### 5.1 Scripts

| Script | Purpose | Wraps |
|--------|---------|-------|
| `scripts/k8s_exec.py` | Execute kubectl commands, capture output | `kubectl` |
| `scripts/parse_runbook.py` | Parse any supported format into `Runbook` dataclass | regex + Claude fallback |
| `scripts/state_tracker.py` | Persist execution state (current step, completed steps, collected outputs) | JSON file |
| `scripts/trace_logger.py` | Log full execution trace for RLM consumption | Append-only JSON log |
| `scripts/approval_gate.py` | Format approval prompts, validate responses | stdout formatting |

### 5.2 k8s_exec.py Contract

```python
def execute_k8s_command(
    command: str,                    # e.g., "kubectl get pods -n default"
    timeout: int = 30,
    capture_output: bool = True,
    dry_run: bool = False
) -> CommandResult:
    """
    Returns CommandResult with:
      - stdout: str
      - stderr: str
      - exit_code: int
      - duration_ms: int
      - command: str (as executed)
      - timestamp: str (ISO 8601)
    """
```

---

## 6. RLM Improvement Loop

This is the Continual Learning track component. After the skill runs (successfully or not), the RLM processes the execution trace to improve the skill.

### 6.1 Flow

```
┌─────────────────────┐
│ Execution completes  │
│ (trace_log.json)     │
└──────────┬──────────┘
           │
     ┌─────▼──────┐
     │ RLM REPL   │  context = full trace log (could be 100K+ tokens)
     │             │  query = "Analyze this execution. Identify failures,
     │  Root LM    │          misinterpretations, and missed steps.
     │  (Opus 4.6) │          Produce specific patches to skill.md and
     │             │          scripts/ to improve future runs."
     └─────┬──────┘
           │
     ┌─────▼──────────────────────────┐
     │ RLM recursively:               │
     │  1. Peeks at trace structure    │
     │  2. Greps for ERROR/FAILED     │
     │  3. Analyzes each failure       │
     │  4. Cross-refs with runbook     │
     │  5. Identifies root causes      │
     │  6. Generates patches           │
     └─────┬──────────────────────────┘
           │
     ┌─────▼──────┐
     │ Output:     │
     │ - Patches   │  (diffs to skill.md, scripts, references)
     │ - Report    │  (human-readable analysis)
     │ - Score     │  (estimated improvement %)
     └─────────────┘
```

### 6.2 What the RLM Analyzes

| Failure Type | Example | RLM Detection Strategy | Skill Patch |
|-------------|---------|----------------------|-------------|
| **Parser miss** | Runbook had a conditional in prose ("if the pod has OOMKilled status...") that parser treated as linear | Grep trace for steps marked SKIPPED or UNEXPECTED_BRANCH | Add pattern to `parse_runbook.py` for prose conditionals |
| **Wrong command** | Skill ran `kubectl logs <pod>` but pod name was a deployment name | Grep for non-zero exit codes + stderr containing "not found" | Add name-resolution logic to `k8s_exec.py` |
| **Missing verification** | Remediation succeeded but skill didn't verify | Compare runbook steps vs executed steps, find gaps | Add VERIFICATION step to skill.md workflow |
| **Timeout** | Command took too long on a large cluster | Grep for TIMEOUT markers | Increase timeout or add `--limit` flags |
| **Misinterpreted output** | kubectl output format changed, pattern match failed | Compare expected_output vs actual stdout | Update expected_output patterns |

### 6.3 RLM Implementation

Use `rlm-minimal` (or `recursive-llm` pip package) as the RLM runtime:

```python
from rlm import RLM

rlm = RLM(
    model="claude-opus-4.6",          # Root LM: smart, good at analysis
    recursive_model="claude-sonnet-4"  # Sub-calls: cheaper, still capable
)

# Load the execution trace as context
with open("trace_log.json") as f:
    trace = f.read()

result = rlm.completion(
    context=trace,
    query="""Analyze this RuneGard execution trace.

    For each failure or suboptimal step:
    1. Identify the root cause
    2. Classify it (parser_miss | wrong_command | missing_verification | timeout | misinterpreted_output | other)
    3. Generate a specific patch (unified diff format) to the relevant file

    Output a JSON object with:
    {
      "failures": [...],
      "patches": [{"file": "...", "diff": "..."}],
      "summary": "...",
      "estimated_improvement": "X%"
    }
    """
)
```

### 6.4 Applying Patches

After RLM outputs patches:
1. Present patches to the user for review (same approval-gate pattern)
2. Apply approved patches to the skill files
3. Re-run the same scenario to measure improvement
4. Log the before/after scores for the demo

---

## 7. Skill Package Structure

```
runegard/
├── skill.md                          # Core skill definition (see §7.1)
├── scripts/
│   ├── parse_runbook.py              # Multi-format runbook parser
│   ├── k8s_exec.py                   # kubectl wrapper with output capture
│   ├── state_tracker.py              # FSM state persistence
│   ├── trace_logger.py               # Execution trace for RLM
│   ├── approval_gate.py              # Human-in-the-loop prompt formatting
│   └── rlm_improver.py              # RLM improvement loop orchestrator
├── references/
│   ├── runbook_formats.md            # Guide: how to detect and parse each format
│   ├── k8s_common_patterns.md        # Common K8s failure patterns and commands
│   └── execution_patterns.md         # Decision tree traversal patterns
├── assets/
│   └── example_runbooks/
│       ├── crashloop_runbook.md       # Demo runbook: KubePodCrashLooping
│       ├── quota_exceeded_runbook.md  # Demo runbook: KubeQuotaExceeded
│       └── pending_pvc_runbook.md     # Demo runbook: stuck PersistentVolumeClaim
└── demo/
    ├── setup_kind_cluster.sh          # Create kind cluster + pre-seed failures
    ├── seed_failures.sh               # Deploy broken workloads
    └── run_demo.sh                    # End-to-end demo script
```

### 7.1 skill.md (Core)

```markdown
---
name: runegard
description: >
  Autonomous runbook executor for Kubernetes operations. Reads runbooks in any
  format (markdown, Confluence wiki, YAML-frontmatter, plain text), parses them
  into executable decision trees, and follows them step-by-step against a live
  K8s cluster. Requests human approval before any mutating action. Includes an
  RLM-powered improvement loop that learns from execution failures.
---

# RuneGard — Kubernetes Runbook Executor

## When to Use This Skill

Use this skill when:
- You have a runbook document describing an operational procedure
- You need to diagnose or remediate a Kubernetes issue
- You want to follow a step-by-step troubleshooting guide against a live cluster

## Workflow

### Phase 1: Parse the Runbook

1. Accept a runbook file or URL from the user
2. Run `scripts/parse_runbook.py` to detect the format and extract the decision tree
3. Present the parsed structure to the user for confirmation:
   - Number of steps detected
   - Decision points identified
   - Commands that will be executed
   - Estimated execution time

### Phase 2: Execute the Runbook

1. Initialize the state tracker via `scripts/state_tracker.py`
2. Begin trace logging via `scripts/trace_logger.py`
3. Walk the decision tree step by step:
   - For DIAGNOSTIC steps: execute automatically, capture output
   - For REMEDIATION steps: invoke `scripts/approval_gate.py`, wait for user approval
   - For VERIFICATION steps: execute automatically, compare against expected output
   - For ESCALATION steps: present escalation info, ask if user wants to continue or hand off
4. At each branch point, evaluate conditions against collected output to choose the next step
5. If any step fails unexpectedly, offer: retry | skip | rollback | abort

### Phase 3: Report Results

1. Present a summary: steps completed, issues found, actions taken, current cluster state
2. Save the full execution trace to `trace_log.json`

### Phase 4: Improve (Optional — Continual Learning)

1. If the execution had failures or suboptimal paths, ask the user:
   "Would you like me to analyze this run and improve the skill for next time?"
2. If yes, run `scripts/rlm_improver.py` with the execution trace
3. Present proposed patches for review
4. Apply approved patches

## Important Rules

- **NEVER** execute a REMEDIATION command without explicit user approval (unless in Auto mode)
- **ALWAYS** log every command and its output to the trace log
- **ALWAYS** check for a rollback path before executing any REMEDIATION step
- If the runbook references tools not available on this system, inform the user and skip those steps
- If a command's output doesn't match any expected pattern, flag it as UNCERTAIN and ask the user how to proceed

## References

- See `references/runbook_formats.md` for format detection and parsing guidance
- See `references/k8s_common_patterns.md` for common K8s failure signatures
- See `references/execution_patterns.md` for decision tree traversal patterns
```

---

## 8. Demo Scenarios

### 8.1 Scenario: KubePodCrashLooping

**Setup:**
```bash
kubectl create deployment broken-app \
  --image=busybox -- /bin/sh -c "exit 1"
```

**Runbook** (`assets/example_runbooks/crashloop_runbook.md`):
```markdown
# Runbook: KubePodCrashLooping

## Trigger
Alert: KubePodCrashLooping — Pod is restarting > 0.5/second

## Steps

### Step 1: Identify the crashing pod
- Run: `kubectl get pods --field-selector=status.phase!=Running -A`
- Look for pods with STATUS = CrashLoopBackOff

### Step 2: Get pod details
- Run: `kubectl describe pod <pod-name> -n <namespace>`
- Check the Events section for:
  - OOMKilled → go to Step 5
  - ImagePullBackOff → go to Step 6
  - Error or CrashLoopBackOff → continue to Step 3

### Step 3: Check container logs
- Run: `kubectl logs <pod-name> -n <namespace> --previous`
- If logs show application error → go to Step 4
- If logs are empty → go to Step 7

### Step 4: Diagnose application error
- Review the error message in logs
- Common causes:
  - Missing environment variable → check ConfigMap/Secret mounts
  - Database connection failure → verify service DNS and network policies
  - Permission denied → check RBAC and SecurityContext
- **Remediation**: Fix the root cause (may require deployment update)

### Step 5: Handle OOMKilled
- Run: `kubectl top pod <pod-name> -n <namespace>` (if metrics-server available)
- **Remediation**: Increase memory limits:
  `kubectl patch deployment <deploy-name> -n <namespace> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container>","resources":{"limits":{"memory":"512Mi"}}}]}}}}'`

### Step 6: Handle ImagePullBackOff
- Run: `kubectl describe pod <pod-name> -n <namespace> | grep -A5 "Events"`
- Verify image name and tag exist
- Check imagePullSecrets if using private registry
- **Remediation**: Fix image reference in deployment spec

### Step 7: Empty logs — check init containers
- Run: `kubectl logs <pod-name> -n <namespace> -c <init-container> --previous`
- If init container is failing, diagnose its logs separately

### Verification
- Run: `kubectl get pods -n <namespace> | grep <pod-name>`
- Confirm STATUS = Running and RESTARTS has stopped incrementing
- Wait 2 minutes and re-check
```

### 8.2 Scenario: KubeQuotaExceeded

**Setup:**
```bash
kubectl create namespace constrained
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tight-quota
  namespace: constrained
spec:
  hard:
    pods: "1"
    requests.cpu: "200m"
    requests.memory: "256Mi"
EOF
kubectl create deployment web --image=nginx --replicas=3 -n constrained
```

**Runbook** (`assets/example_runbooks/quota_exceeded_runbook.md`):
```markdown
# Runbook: KubeQuotaExceeded

## Trigger
Alert: KubeQuotaExceeded — Resource usage > 90% of quota in namespace

## Steps

### Step 1: Check quota usage
- Run: `kubectl describe quota -n <namespace>`
- Identify which resource is at/over limit (pods, cpu, memory)

### Step 2: List resource consumers
- Run: `kubectl top pods -n <namespace> --sort-by=memory`
- Run: `kubectl get pods -n <namespace> -o wide`
- Identify pods consuming the most resources

### Step 3: Evaluate options
- If non-critical pods can be evicted → go to Step 4
- If quota needs increasing → go to Step 5
- If deployment needs right-sizing → go to Step 6

### Step 4: Evict non-critical pods
- **Remediation**: `kubectl delete pod <pod-name> -n <namespace>`
- Verify quota usage decreased

### Step 5: Increase quota
- **Remediation**: `kubectl patch resourcequota <quota-name> -n <namespace> -p '{"spec":{"hard":{"pods":"10"}}}'`
- Verify with: `kubectl describe quota -n <namespace>`

### Step 6: Right-size deployments
- **Remediation**: Reduce replica count or resource requests
- `kubectl scale deployment <name> -n <namespace> --replicas=<N>`
```

### 8.3 Scenario: Stuck PersistentVolumeClaim

**Setup:**
```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: stuck-pvc
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
  storageClassName: nonexistent-class
EOF
```

**Runbook** (`assets/example_runbooks/pending_pvc_runbook.md`):
```markdown
# Runbook: PersistentVolumeClaim Stuck in Pending

## Trigger
PVC has been in Pending state for > 5 minutes

## Steps

### Step 1: Check PVC status
- Run: `kubectl get pvc`
- Run: `kubectl describe pvc <pvc-name>`
- Check Events section for provisioning errors

### Step 2: Diagnose the cause
- If "no persistent volumes available" → go to Step 3
- If "storageclass not found" → go to Step 4
- If "waiting for first consumer" → go to Step 5

### Step 3: No PV available
- Run: `kubectl get pv`
- Check if there are available PVs with matching access mode and capacity
- **Remediation**: Create a matching PV or install a dynamic provisioner

### Step 4: StorageClass not found
- Run: `kubectl get storageclass`
- List available storage classes
- **Remediation**: Either create the missing StorageClass or patch the PVC to use an existing one:
  - Delete and recreate PVC with correct storageClassName
  - `kubectl delete pvc <pvc-name>`
  - `kubectl apply -f <fixed-pvc.yaml>`

### Step 5: WaitForFirstConsumer
- This is normal behavior for some StorageClasses
- Check if there is a Pod trying to use this PVC
- If no pod exists, create one; the PVC will bind when scheduled
```

---

## 9. Implementation Plan (Time-Boxed)

| Phase | Time | Deliverable |
|-------|------|-------------|
| **1. Scaffold** | 30 min | `skill.md`, directory structure, empty scripts, `kind` cluster + seeded failures |
| **2. Parser** | 60 min | `parse_runbook.py` — markdown parser with LLM fallback, outputs `Runbook` dataclass |
| **3. Execution Engine** | 90 min | `state_tracker.py` + main execution loop in skill.md workflow, interactive approval gate |
| **4. Tool Bridge** | 30 min | `k8s_exec.py` wrapping kubectl with output capture and trace logging |
| **5. Demo Runbooks** | 30 min | Three runbooks (§8.1–8.3) written and tested against kind cluster |
| **6. RLM Loop** | 60 min | `rlm_improver.py` — wire up `rlm-minimal` to analyze traces and output patches |
| **7. Integration Test** | 30 min | End-to-end: parse → execute → fail → RLM improve → re-execute → succeed |
| **8. Polish** | 30 min | Demo script, README, any rough edges |
| **Total** | **~6 hours** | |

---

## 10. Dependencies

```
# Python packages
anthropic              # Claude API client (for LLM fallback parsing)
recursive-llm          # or clone rlm-minimal — RLM runtime
pyyaml                 # YAML frontmatter parsing
rich                   # Terminal formatting for approval gates

# System tools (pre-installed or brew install)
kind                   # Kubernetes in Docker
kubectl                # K8s CLI
docker                 # Required by kind
```

---

## 11. Judging Criteria Alignment

| Hackathon Criterion | How RuneGard Addresses It |
|---------------------|--------------------------|
| **Is it a proper skill?** | Yes — full `skill.md` standard package with scripts, references, and assets |
| **Does it solve a real problem?** | SRE teams spend hours manually following runbooks during incidents. RuneGard automates this. |
| **Continual Learning track** | RLM loop analyzes failure trajectories and auto-patches the skill. Measurable improvement across iterations. |
| **Data track** | Three realistic K8s failure scenarios with detailed runbooks serve as SkillsBench-compatible task data |
| **Demoability** | Live on a MacBook: kind cluster with pre-broken workloads → skill follows runbook → fixes issues → RLM improves skill |
| **Technical impressiveness** | Multi-format parser, FSM execution, human-in-the-loop approval, RLM recursive analysis |

---

## 12. Stretch Goals (If Time Permits)

- **Runbook Generator**: Reverse the flow — given a K8s alert and cluster state, *generate* a runbook, then execute it
- **Multi-cluster**: Support kubeconfig context switching for multi-cluster runbooks
- **Slack/Discord Integration**: Post approval requests to a channel, receive approvals via emoji reactions
- **Runbook Diff**: When RLM suggests improvements to the runbook itself (not just the skill), output a PR-ready diff

---

## 13. Commands to Get Started

```bash
# 1. Create project
mkdir runegard && cd runegard

# 2. Set up kind cluster
kind create cluster --name runegard-demo

# 3. Seed failures
kubectl create deployment broken-app --image=busybox -- /bin/sh -c "exit 1"
kubectl create namespace constrained
kubectl apply -f quota.yaml
kubectl apply -f stuck-pvc.yaml

# 4. Install Python deps
pip install anthropic recursive-llm pyyaml rich

# 5. Open in Claude Code and point it at this spec
claude

# In Claude Code:
> Read the spec at runegard-spec.md and implement RuneGard following the
> implementation plan in §9. Start with Phase 1 (scaffold) and proceed
> sequentially. After each phase, verify by running the relevant test.
> Use Claude Opus 4.6 for any LLM calls.
```

---

*"Guard your runes, guard your systems."* 🛡️
