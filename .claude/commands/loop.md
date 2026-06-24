---
description: Run the builder and checker in a loop until all checks pass
argument-hint: <task>
allowed-tools: Read, Grep, Glob, Bash, Task
model: opus
---

Run this task as a build-test-fix loop: $ARGUMENTS

1. Write a one-line brief: goal, files in scope, and the **definition of done** (which checks
   must be green for THIS task — not always the full suite; some intermediate steps only need
   a scoped check, e.g. "models import cleanly" or "migration round-trips"). State the area
   (`apps/api` or `apps/web`) so the checker runs the right commands.
2. Dispatch the `builder` subagent to implement the task.
3. Dispatch the `checker` subagent to run the checks for that area against the definition of done.
4. If the checker says `ALL GREEN`: stop and show me the checker's final output.
5. If the checker says `FAILED`: send the exact failure lines to the `builder` to fix, then go
   back to step 3.
6. Repeat up to 5 cycles. Print `Cycle N of 5` out loud at each iteration.

Stop conditions are in CLAUDE.md ("Loop stop rules"). Follow them exactly. Never report success
without the checker's output from the final cycle. Never weaken a check to reach green.
