# Goals

These are the standing directions `django-mvp-payments` works toward. Each one is a capability or
quality to steer by, not a task that gets ticked off. Whether any goal has been served well enough
is decided in the roadmap, the feature specs, and review, never by the goal itself.

This file carries no version numbers or release plan; that lives in the roadmap. For what the
package is, what it stays out of, and the principles that settle a close call, read the
*Scope & philosophy* section of the [README](README.md).

Importance is a tag on each goal, not a ranking:

- **Essential** — not worth adopting without it.
- **Expected** — a complete, dependable version is expected to have it.
- **Aspirational** — a genuine want whose absence never makes the package incomplete.

| ID | Goal | Importance | Status | Notes |
|----|------|------------|--------|-------|
| G1 | A project using a supported payment backend gets that backend's pages, looking like the rest of its django-mvp site, without building them | Essential | | |
| G2 | At least one payment backend is supported | Essential | | drf-stripe-subscription, chosen in [ADR 0009](docs/adr/0009-drf-stripe-subscription-is-the-first-backend.md) |
| G3 | More than one payment backend is supported | Aspirational | | Which one waits for a project that needs it |

_Written 2026-09-24. Revise as the goals change._
