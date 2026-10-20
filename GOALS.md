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
| G1 | A project using a supported payment provider gets that provider's pages, looking like the rest of its django-mvp site, without building them | Essential | | |
| G2 | At least one payment provider is supported, with the records behind its pages kept by this package | Essential | | Stripe, through the package's own `mvp_payments.stripe` app ([ADR 0010](docs/adr/0010-the-package-ships-its-own-stripe-app.md)) |
| G3 | More than one payment provider is supported | Aspirational | | Which one waits for a project that needs it. It arrives as another provider app, or as a third-party package shipping its own templates |

_Written 2026-09-24. Revise as the goals change._
