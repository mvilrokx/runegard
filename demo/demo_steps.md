# RuneGard — Demo Steps

## Before the demo

1. **Set up the K8s cluster** (do this well before presenting):
   ```
   bash demo/setup_cluster.sh
   ```
   This creates the broken pods (crash-looping, OOM) in your cluster.

2. **Clear any previous learned patterns**:
   ```
   echo "# Learned Patterns" > references/learned_patterns.md
   ```

3. **Delete any old trace logs**:
   ```
   rm -f trace_log.json
   ```

4. **Verify pods are broken**:
   ```
   kubectl get pods -A
   ```
   You should see `broken-app` and `oom-pod` in CrashLoopBackOff.

5. **Start the slide deck** (in a separate terminal):
   ```
   cd demo && python3 -m http.server 8765
   ```
   Open `http://localhost:8765/deck.html` in browser. Press `f` for fullscreen.

6. **Set your API key**:
   ```
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

## During the demo

### Slides 1–3: Talk through the slides (60s)

Just present — no live commands. Arrow keys to advance.

### Slide 4: Run 1 — show it failing (20s)

This slide shows pre-baked output. Talk through it:
- "The skill loaded, parsed 8 steps"
- "It found the broken pods but couldn't resolve template variables"
- "It missed the OOMKilled branch and took the wrong path"
- "But it produced a trace"

**Optional live demo** (if time allows, replace this slide with a live run):
```
uv run python -m runegard run assets/runbooks/crashloop.md
```

### Slide 5: Run the improve step (20s)

This slide shows pre-baked output. Talk through it:
- "We feed the trace into Claude"
- "It learned 4 patterns"
- "Patterns saved to a file for next time"

**Optional live demo**:
```
uv run python -m runegard improve trace_log.json --runbook assets/runbooks/crashloop.md
```
Then type `yes` when prompted to apply patterns.

### Slide 6: Run 2 — show it succeeding (25s)

This slide shows pre-baked output. Talk through it:
- "Same runbook, but now it reads the learned patterns"
- "Extracts real pod names, branches correctly"
- "Asks for approval before patching"

**Optional live demo** (as a Claude Code skill):
```
claude
> Run the crashloop runbook against my cluster
```
Type `approve` when it asks for permission to patch.

### Slide 7: Close (15s)

Present the RLM loop diagram and tech stack. Wrap up.

## After the demo

To reset everything for another run:
```
echo "# Learned Patterns" > references/learned_patterns.md
rm -f trace_log.json
bash demo/setup_cluster.sh
```
