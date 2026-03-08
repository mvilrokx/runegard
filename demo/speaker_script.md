# RuneGard — Speaker Script (2:30)

## Slide 1: Title (10s)

"RuneGard — an autonomous runbook executor that gets smarter every time it runs."

## Slide 2: The Problem (25s)

"When something breaks at 3am, an on-call engineer wakes up, opens a runbook in the wiki, and starts copying commands into a terminal. They read the output, decide the next step, paste the next command — over and over. It's manual, it's slow, it's error-prone. And worst of all — the next time this happens, it starts from scratch. Nobody learned anything."

## Slide 3: The Solution (25s)

"RuneGard reads the same markdown runbook your team already has. It uses Claude to parse it into a decision tree — steps, branches, expected outputs. Then it executes it. Diagnostic steps run automatically. But anything that mutates state — a deployment patch, a restart — requires explicit human approval before it runs. Everything gets logged into a trace."

## Slide 4: Demo Run 1 (20s)

"Here's what the first run looks like. The skill loads, parses 8 steps, and starts executing. It lists the pods, finds the crash-looping ones. But then it hits a command with template variables — `<pod-name>` — and can't resolve them. It goes straight through linearly and misses the OOMKilled branch entirely. It took the wrong path. But it produced a trace of everything it did."

## Slide 5: The RLM Loop (20s)

"We feed that trace back into Claude. It analyzes what went wrong and identifies four patterns — like 'extract pod names from step 1 output' and 'empty stdout means you missed something.' These patterns get saved to a file. This is the learning step."

## Slide 6: Demo Run 2 (25s)

"Second run — same runbook. But now it loads the learned patterns first. It extracts the real pod name from the output, detects OOMKilled, branches correctly to step 5, and asks for approval before patching the deployment. Same runbook, smarter execution."

## Slide 7: Closing (15s)

"Every run produces a trace. Every trace feeds the improvement loop. The skill genuinely gets better with every incident. RuneGard — autonomous runbook execution with continual learning. Built with Python, Claude API, and standard markdown runbooks."
