# Subagents

Project-level custom subagents for the VGains gym app. Each `*.md` here defines a
specialist your **main interactive Claude session** can delegate to. The main
session is the orchestrator — it reads each agent's `description` and either
hands off automatically or you ask for one by name.

## Roster

| Agent | Use it for | Tools |
|---|---|---|
| `api-builder` | FastAPI backend changes in `apps/api` | file + bash |
| `web-builder` | Next.js changes in `apps/web` | file + bash |
| `ios-builder` | SwiftUI changes in `apps/ios/GymApp` | file + bash |
| `task-runner` | Implement one numbered `tasks/` spec end-to-end | file + bash |
| `code-reviewer` | Adversarial correctness + conventions review | **read-only** |

## How to invoke

- **Automatic**: just describe the work ("update the workouts router to add
  cursor pagination") and the main session picks `api-builder` from its
  description.
- **Explicit**: name it — "use the code-reviewer subagent on my changes" or
  "have task-runner implement tasks/05-analytics/03-foo.md".
- **Parallel**: independent work fans out — "build the API change with
  api-builder and the iOS screen with ios-builder" runs both at once.

Subagents return their final message to the orchestrator as **data** (a summary
of files changed, commands run, results), not to you directly — the main session
relays what matters.

## The build → review → fix pattern

There is no separate "fixer" agent — it's an orchestration loop the main session
runs:

1. **Build** — dispatch the matching builder (`api-builder` / `web-builder` /
   `ios-builder`) or `task-runner` to implement the change.
2. **Review** — dispatch `code-reviewer` on the resulting diff. It returns
   findings (read-only; it never edits).
3. **Fix** — dispatch the *same builder* again with the findings to apply fixes.
   Repeat 2–3 until the reviewer says SHIP.

Ask for it directly: *"Implement X with api-builder, then review→fix until the
code-reviewer signs off."*

## Subagents vs. Workflow scripts

- **These subagents** = interactive, model-driven orchestration. The main session
  decides what to delegate, in what order, based on the conversation. Good for
  ad-hoc and exploratory work.
- **`../wf-*.js` Workflow scripts** = deterministic orchestration. The script
  hard-codes the control flow (pipeline / parallel / loops). Good for a
  repeatable multi-stage process.
- They compose: a Workflow `agent()` call can target one of these roles via its
  `agentType` option (e.g. `agent(prompt, { agentType: 'code-reviewer' })`), so a
  script can drive the same specialists this README describes.

## Editing these

Each file is frontmatter (`name`, `description`, `tools`, `model`) + a system
prompt. The `description` is what drives auto-delegation — keep it specific about
*when* to use the agent. `tools` restricts what the agent may call (omit to
inherit everything). `model: inherit` uses whatever the main session is on.
