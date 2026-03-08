---
marp: true
theme: uncover
class: invert
paginate: true
style: |
  section {
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  }
  h1 {
    color: #58a6ff;
  }
  h2 {
    color: #8b949e;
    font-size: 0.9em;
  }
  .mermaid {
    display: flex;
    justify-content: center;
    margin: 0.5em 0;
  }
  .mermaid svg {
    max-height: 400px;
  }
  pre {
    font-size: 0.65em;
    background: #161b22;
    border-radius: 8px;
    padding: 1em;
  }
  .tech-stack {
    font-size: 0.7em;
    columns: 2;
  }
  .small {
    font-size: 0.6em;
    color: #8b949e;
  }
---

<!-- _class: invert lead -->

# RuneGard

### Autonomous K8s Runbook Executor
### with Continual Learning

<br>

*"It gets smarter every time it runs"*

---

# It's 3am. Your pod is crash-looping.

<div class="mermaid">
graph LR
    A["🚨"] --> B["😴"] --> C["📖"] --> D["📋"] --> E["💻"] --> F["🤔"] --> G{"🔄"}
    G --> D
    style A fill:#f85149,color:#fff
    style G fill:#d29922,color:#fff
</div>

*Alert → Wake up → Open wiki → Copy cmd → Paste → Read output → Repeat*

Manual. Slow. Error-prone. **Doesn't learn from past incidents.**

---

# RuneGard: The Solution

<div class="mermaid">
graph LR
    A["📄"] --> B["🧠"] --> C["🌳"] --> D["⚡"] --> E{"❓"}
    E -->|"safe"| F["✅"]
    E -->|"risky"| G["🔒"]
    F --> H["📊"]
    G --> H
    style A fill:#238636,color:#fff
    style G fill:#d29922,color:#fff
    style B fill:#1f6feb,color:#fff
</div>

*Runbook → Claude Parser → Decision Tree → Executor → Safe? Auto-run : **Human Approval** → Trace*

---

# Demo: Run 1 — Learning from failure

```
⏺ Skill(runegard) — loaded

⏺ Parsed 8 steps. Decision points:
    OOMKilled → Step 5
    ImagePullBackOff → Step 6

⏺ kubectl get pods -A
  broken-app   0/1   CrashLoopBackOff   11
  oom-pod      0/1   CrashLoopBackOff   9

⏺ kubectl describe pod <pod-name> -n <namespace>
  ⚠ Command has template variables — can't resolve

  Steps executed: step-1, step-2, step-3, step-4, step-8
  ❌ Missed OOMKilled branch. Took wrong path.
```

First run hits gaps. **But it produced a trace.**

---

# The RLM Loop: What went wrong?

```
$ runegard improve trace_log.json --runbook crashloop.md

ANALYSIS SUMMARY
═══════════════════════

New patterns learned: 4
  - Extract pod names from Step 1 output for subsequent commands
  - "May require deployment update" → prompt, don't execute
  - Verify restart counts over time, not just status
  - Empty stdout = missing pod identification

Apply learned patterns? yes
✅ Patterns appended to references/learned_patterns.md
```

Claude analyzes the trace. **Writes down what it learned.**

---

# Demo: Run 2 — Applying what it learned

```
⏺ Skill(runegard) — loaded
  📚 Applying 4 learned patterns from previous runs

⏺ kubectl get pods -A
  Found: broken-app (CrashLoopBackOff), oom-pod (OOMKilled)

⏺ kubectl describe pod oom-pod -n default
  ✅ Extracted real pod name from Step 1
  ✅ Detected OOMKilled → branching to Step 5

  APPROVAL REQUIRED — Handle OOMKilled
  Command: kubectl patch deployment ... memory: 512Mi
  Rollback: kubectl rollout undo deploy

  Type 'approve', 'skip', or 'abort': approve ✅
```

**Same runbook. Smarter execution.**

---

<!-- _class: invert lead -->

# It gets better every time

<div class="mermaid">
graph TD
    A["▶️ Run"] --> B["📊 Trace"]
    B --> C["🧠 Learn"]
    C --> D["📚 Apply"]
    D --> A
    style A fill:#238636,color:#fff
    style C fill:#1f6feb,color:#fff
    style D fill:#d29922,color:#fff
</div>

<div class="tech-stack">

**Python 3.12** · **Claude API** · **kubectl**
**Markdown runbooks** · **RLM feedback loop**

</div>

<br>

**RuneGard** — autonomous runbook execution with continual learning.

---

<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
mermaid.initialize({
  startOnLoad: true,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#1f6feb',
    primaryTextColor: '#c9d1d9',
    primaryBorderColor: '#30363d',
    lineColor: '#8b949e',
    secondaryColor: '#161b22',
    tertiaryColor: '#0d1117',
    fontFamily: 'SF Mono, Fira Code, monospace',
    fontSize: '14px'
  }
});
</script>
