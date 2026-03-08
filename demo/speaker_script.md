# RuneGärd — Speaker Script (2:00)

## Slide 1: Title (5s)

"RuneGärd — an autonomous runbook executor that gets smarter every time it runs."

## Slide 2: The Problem (25s)

"When a service crashes in the middle of the night — stuck restarting in a loop — someone gets paged. Most teams have runbooks for this: step-by-step troubleshooting guides, like a recipe. But today a human follows that recipe manually. Wake up, open the wiki, copy a command, paste it, read the output, decide the next step, repeat. It's slow, it's error-prone, and the worst part — next time, it starts from scratch. Nobody learned anything."

## Slide 3: The Solution (20s)

"RuneGärd takes those same markdown runbooks and executes them autonomously. Claude parses the runbook into a decision tree, then runs through it. Safe commands execute automatically. Anything risky stops and asks for human approval first. Everything gets logged into a trace."

## Slide 4: Demo Run 1 (15s)

"First run against our broken cluster. It finds the crashing services but hits a gap — the runbook has a placeholder it can't fill. It takes the wrong path and misses the real issue. But it logged everything into a trace."

## Slide 5: The CL Loop (15s)

"We feed that trace into Claude. It figures out what went wrong — 'grab the pod name from step 1,' 'empty output means you missed something.' Four patterns identified and saved. This is the continuous learning step."

## Slide 6: Demo Run 2 (20s)

"Same runbook, second run. It loads the learned patterns, grabs the real pod name, recognizes the out-of-memory error, takes the correct branch, and asks: 'I want to increase this service's memory — approve?' Same runbook, smarter execution."

## Slide 7: Closing (10s)

"Every run produces a trace. Every trace feeds the loop. It gets better with every incident. RuneGärd — autonomous runbook execution with continual learning."
