# Gym App Build Plan

A training operating system for me and my gym buddies. Tracks workouts, builds programs, analyzes progression, logs food, and pulls in Fitbit data. Web (Next.js) and iOS (Swift) clients sharing a Python FastAPI backend.

## Stack

- Backend: Python 3.12 + FastAPI + SQLAlchemy + Alembic
- Database: Postgres 16
- Auth: Apple Sign-In + Google Sign-In via OAuth, JWT session tokens
- Web: Next.js 15 (App Router) + TypeScript + Tailwind
- iOS: Swift 6 + SwiftUI, native iOS 17+ components
- AI: Self-hosted Ollama on a Hetzner VPS (Llama 3.1 8B / Qwen 2.5 for text)
- Hosting: Hetzner VPS for API + Ollama, Vercel for web, TestFlight for iOS
- Design language: iOS-native feel everywhere (SF Symbols, system blur, native components on iOS, Tailwind tokens that mirror them on web)

## Phasing

Build is phased so each layer ships usable on its own.

1. Foundation: API skeleton, auth, exercise library, deployment baseline
2. Tracking: log workouts on web and iOS
3. Programming: template library + manual program builder
4. Progression: linear, double-progression, RPE-based, mesocycles, deloads, continuous (never-ending) mode
5. Analytics: strong/weak point analysis, per-muscle volume, stagnation detection
6. Nutrition: FatSecret search + barcode, structured meal plans, fast plan logging and flexible tracking
7. Fitbit: import workouts/HR/steps, push workouts back, readiness gauge

iOS work is split per-phase under `08-ios/` so the Swift app catches up incrementally rather than as one monolithic task.

Onboarding and the public landing page live under `10-onboarding/`.

## Task index

- `00-overview/` - this file, data model, API conventions, design system
- `01-foundation/` - repo setup, FastAPI skeleton, Postgres, auth, exercise library, CI
- `02-tracking/` - workout sessions, sets, all exercise types
- `03-programming/` - templates, manual builder, scheduling
- `04-progression/` - progression engines and recommendations, block or continuous lifecycle
- `05-analytics/` - heuristics first, LLM explanations layered on
- `06-nutrition/` - FatSecret food API, barcode, structured meal plans, fast and flexible logging
- `07-fitbit/` - OAuth, sync workers, readiness scoring
- `08-ios/` - Swift app, one folder per phase
- `09-deployment/` - VPS provisioning, Vercel, observability, backups
- `10-onboarding/` - interactive product tour, public landing page

## How to use these files with Claude Code

Each task file is self-contained: context, goal, deliverables, acceptance criteria, and dependencies on other tasks. Point Claude Code at one file at a time. Don't paste the whole tree at once. The dependency graph at the bottom of each file tells you what must be done first.

## Style rules

- No em dashes or en dashes in prose anywhere (code comments, READMEs, UI copy).
- Concise plain language. Direct answers before explanations.
- Sentence case headings.
- Python: ruff + black, type hints everywhere, Pydantic v2 models.
- TypeScript: strict mode, no `any`, Zod for runtime validation.
- Swift: SwiftUI-first, async/await, no Combine unless required.
