# Progress — 002 Show a person the subscription they are on

A narrative of the run, newest entry at the bottom. The ledger
(`feature-state.json`) is the machine record; this file is what a person reads to understand how
the feature got where it is.

## 2026-09-22 — S3 PLAN

Opened from the feature queue, which reported the feature ready with no dependencies outstanding
and no feature delivered in this repository since the specification landed, so there was nothing to
re-read the specification against.

The branch starts at `a5ac07fc3fdf0853787f41ee3eacff5101f2c182`, which is the merge of the
specification pull request (#17) and the current tip of the default branch. The verifier was green
on that commit before anything was written: lint, typecheck, the full suite, build and conformance
all passed.

Planning read the backend's models, its URL configuration and its billing-portal view, django-mvp's
component library, and this repository's standards document. What came out of it is in
`research.md`; the three readings that shaped the design were that the backend already exposes its
own definition of a current subscription as a property, that an amount arrives as an integer in a
currency's minor unit with no rendering attached, and that the portal endpoint answers a POST and
carries no route name, so it cannot be reversed and has to be supplied by the project.
