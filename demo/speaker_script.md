# RuneGard — Speaker Script (2:30)

## Slide 1: Title (10s)

"RuneGard — an autonomous runbook executor that gets smarter every time it runs."

## Slide 2: The Problem (30s)

"Imagine you're running a web service — an online store, an API, anything. In the middle of the night, one of your services starts crashing. It tries to restart, crashes again, restarts, crashes — stuck in a loop. Your monitoring fires an alert and someone gets paged.

Now, most teams have *runbooks* for this — step-by-step troubleshooting guides. Think of it like a recipe: first check this, then run that command, if you see X do Y. But today, a human has to follow that recipe manually — wake up, open the wiki, copy a command, paste it, read the output, decide the next step, repeat. It's slow, it's 3am, mistakes happen. And the worst part? Next time the same thing breaks, it starts from scratch. Nobody learned anything."

## Slide 3: The Solution (25s)

"RuneGard takes those same runbooks your team already writes — plain markdown files — and executes them autonomously. It uses Claude to parse the runbook into a decision tree with steps, branches, and expected outputs. Then it runs through them. Safe diagnostic commands execute automatically. But anything risky — like restarting a service or changing a configuration — stops and asks a human for approval first. And every action gets logged into a trace."

## Slide 4: Demo Run 1 (20s)

"Here's what happens the first time RuneGard runs a runbook against our broken cluster. It finds the crashing services, but hits a gap — the runbook says 'describe pod-name' but it doesn't know *which* pod yet. It can't fill in the blank, so it takes the wrong path and misses the real issue — one pod is running out of memory. But here's the key: it logged everything it did into a trace."

## Slide 5: The CL Loop (20s)

"Now we feed that trace back into Claude. It looks at what happened and figures out what went wrong — 'you should have grabbed the pod name from the first step's output,' 'empty output means you missed something.' It identifies four patterns and writes them down. This is the learning step — continuous learning from real executions."

## Slide 6: Demo Run 2 (25s)

"We run the same runbook again. This time RuneGard loads those learned patterns first. It grabs the real pod name from the output, recognizes the out-of-memory error, takes the correct branch, and stops to ask: 'I want to increase this service's memory limit — here's the command and here's how to undo it. Approve?' Same runbook, smarter execution."

## Slide 7: Closing (10s)

"Every run produces a trace. Every trace feeds the loop. It genuinely gets better with every incident. RuneGard — autonomous runbook execution with continual learning."
