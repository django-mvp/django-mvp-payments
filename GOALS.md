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
| G1 | Adding a backend to a project takes minimal setup and no page-building | Essential | | |
| G2 | Both a native interface and the provider's own embed are first-class ways to get a working page | Essential | | |
| G3 | One backend's pages never affect another's | Essential | | |
| G4 | Whatever the installed backend can do, there is a page for it | Expected | | |

_Written 2026-09-21. Revise as the goals change._
