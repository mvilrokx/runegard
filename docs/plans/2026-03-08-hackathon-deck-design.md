# Hackathon Pitch Deck Design

**Format:** Marp markdown → HTML slides
**Duration:** 2 minutes 30 seconds
**Audience:** Hackathon jury, no K8s/SRE background assumed
**Tool:** Marp CLI (`npx @marp-team/marp-cli`)

## Narrative Arc

1. **The Problem** (30s) — manual runbook execution at 3am
2. **The Solution** (30s) — RuneGard parses and executes runbooks autonomously
3. **Demo: First Run** (20s) — skill runs, hits gaps, produces trace
4. **Demo: Improve** (20s) — RLM loop identifies failures, learns patterns
5. **Demo: Second Run** (20s) — skill applies learned patterns, works correctly
6. **Architecture + Close** (20s) — RLM feedback loop diagram, tech stack

## Slides

### Slide 1: The Problem
- Mermaid flowchart: alert → engineer wakes → opens wiki → copies commands → pastes → reads output → decides → repeats
- Speaker note: "When K8s breaks at 3am, an on-call engineer opens a markdown runbook and manually copies commands into a terminal."

### Slide 2: The Solution
- Mermaid flowchart: markdown runbook → parser (Claude API) → decision tree → executor → human approval gate → trace log
- Speaker note: "RuneGard reads the same markdown runbook, parses it into a decision tree, executes it against your cluster — pausing for approval before anything destructive."

### Slide 3: Demo — First Run
- Terminal screenshot: skill executing, hitting placeholder issues, going linear
- Speaker note: "First run hits a gap — template variables the executor can't fill. It completes but takes the wrong path."

### Slide 4: Demo — Improve
- Terminal screenshot: improve output showing 4 learned patterns
- Speaker note: "We feed the trace into Claude. It identifies failures and writes down what it learned."

### Slide 5: Demo — Second Run
- Terminal screenshot: skill correctly extracting pod names, branching on OOMKilled, asking approval
- Speaker note: "Second run reads learned patterns, substitutes real pod names, branches correctly, asks before patching."

### Slide 6: Architecture + Close
- Mermaid cycle diagram: Run → Trace → Improve → Learned Patterns → Run
- Tech stack list
- Speaker note: "Every run produces a trace. Every trace feeds the loop. The skill gets better with every incident."

## Technical Details

- Single markdown file: `demo/deck.md`
- Render: `npx @marp-team/marp-cli demo/deck.md --html --allow-local-files`
- Terminal screenshots: captured from actual runs, stored in `demo/screenshots/`
- Mermaid diagrams: inline in markdown, rendered by Marp's HTML mode
