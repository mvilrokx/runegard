# RuneGärd — Demo Steps

Everything runs inside Claude Code. No CLI commands needed during the demo.

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

6. **Set your API key** and open Claude Code:
   ```
   export ANTHROPIC_API_KEY=sk-ant-...
   claude
   ```

## During the demo

### Slides 1–3: Talk through the slides (60s)

Just present — no live commands. Arrow keys to advance.

### Slide 4: Run 1 — first attempt (20s)

The slide shows pre-baked output. Talk through it. If doing a live demo, type in Claude Code:

```
Run the crashloop runbook against my cluster
```

Claude will load the RuneGärd skill, parse the runbook, and start executing.
It will hit template variables it can't resolve and take the wrong path.
Point out: "It failed — but it produced a trace."

### Slide 5: Improve — learn from the failure (20s)

The slide shows pre-baked output. Talk through it. If doing a live demo, type in Claude Code:

```
Analyze the trace and improve the skill for next time
```

Claude will analyze the trace, identify 4 patterns, and ask if you want to save them.
Say "yes" — the patterns get written to `references/learned_patterns.md`.

### Slide 6: Run 2 — second attempt with learned patterns (25s)

The slide shows pre-baked output. Talk through it. If doing a live demo, type in Claude Code:

```
Run the crashloop runbook again
```

Claude will load the learned patterns, extract real pod names, branch correctly
on the out-of-memory error, and ask for approval before patching.
Type `approve` when prompted.

Point out: "Same runbook. Smarter execution."

### Slide 7: Close (15s)

Present the CL loop diagram and tech stack. Wrap up.

## After the demo

To reset everything for another run:
```
echo "# Learned Patterns" > references/learned_patterns.md
rm -f trace_log.json
bash demo/setup_cluster.sh
```
