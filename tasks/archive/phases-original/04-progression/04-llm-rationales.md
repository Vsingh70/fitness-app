# 04.04 LLM rationale generation

## Context

Heuristics produce a `ProgressionDecision` with a `rationale_key` (e.g. `linear.success.increment`). For the user-facing copy, we generate a one-sentence natural-language explanation using a self-hosted LLM via Ollama. This keeps the math deterministic and the prose readable.

## Goal

A small service that takes a decision + context and returns a friendly explanation, with template-based fallbacks if the LLM is unavailable.

## Setup

Ollama runs on the same VPS as the API. Default model: `qwen2.5:7b-instruct` (or `llama3.1:8b-instruct-q5` if memory allows).

## Service

`apps/api/app/services/ai/rationales.py`:

```python
async def generate_rationale(
    decision: ProgressionDecision,
    context: RationaleContext,  # exercise name, prior weight, history snapshot
) -> str:
    ...
```

- Single Ollama call with a structured prompt that includes:
  - Decision summary (in plain numbers).
  - Last 3 sessions snapshot.
  - Style constraints: "One sentence. No emojis. No exclamation marks. No em dashes. Direct."
- Validate the output: max 200 chars, no banned characters.
- On any failure (Ollama down, validation fails), return a template string keyed by `rationale_key`.

## Template fallbacks

Ship a default English copy file `apps/api/app/services/ai/fallbacks.yaml`:

```yaml
linear.success.increment: "You hit all sets, so weight is going up by {increment_kg} kg next time."
linear.fail.repeat: "You missed reps on at least one set, so weight stays the same next session."
linear.fail.deload: "Two misses in a row, so weight drops 10 percent next session for a reset."
double_progression.advance: "You hit the top of the rep range on all sets, so weight goes up and reps reset to {reps_low}."
double_progression.add_rep: "Add one rep on your weakest set next session."
rpe.under: "RPE was below your target range, so weight goes up by 2.5 percent."
rpe.over: "RPE was above your target, so weight stays and we focus on reps."
rpe.way_over: "RPE was a lot higher than target, so weight drops 5 percent next session."
fatigue.deload: "Recent fatigue signals look high, so a deload week is recommended."
```

These also serve as exemplar style for the LLM to imitate.

## Job

After the orchestrator writes a `recommendations` row with `rationale = NULL`, an ARQ job picks it up, calls `generate_rationale`, and updates the row. Decoupling means saving a session doesn't block on LLM latency.

## Endpoints

No new endpoints. The recommendation API from 04.01 surfaces the rationale once filled.

## Deliverables

1. Ollama client wrapper in `apps/api/app/clients/ollama.py` (single async function, retries, timeout).
2. `generate_rationale` service.
3. ARQ task `rationalize_recommendation`.
4. Fallback yaml and renderer.
5. Tests:
   - Mock Ollama returning bad output -> falls back.
   - Mock Ollama returning good output -> stored as-is.
   - Renderer interpolates variables correctly.

## Acceptance criteria

- A new recommendation gets a rationale within 10 seconds in normal conditions.
- API outage on Ollama does not block recommendations; fallback prose appears immediately.
- Output never contains em dashes, en dashes, or emojis.

## Dependencies

- `04.01`, `04.02`, `04.03`

## Out of scope

- LLM-generated full program critiques (later analytics task).
