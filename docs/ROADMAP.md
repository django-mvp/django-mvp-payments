# Roadmap — django-mvp-payments

**Date:** 2026-09-24

This document was designed against [GOALS.md](../GOALS.md). See also [CONTEXT.md](../CONTEXT.md)
for domain terminology and [CONSTITUTION.md](../CONSTITUTION.md) for project standards.

The roadmap is deliberately short. It says which backends are supported and in what order, not
which pages each one gets. What a backend's pages need to do is decided by the projects that use
them, and is tracked as issues rather than planned here in advance.

## Versioning

| Version | Gate |
|---|---|
| `0.0.x` | Building toward the first backend. Pre-viable, expect churn, nothing published. |
| `0.1.0` | R1 and R2 delivered: one backend fully supported. The first publish. |
| `0.x` | Fixes and additions that projects using the package ask for. |
| `1.0.0` | The package's settings, components and context names have held steady through at least one real project using it. |
| `1.x` | Stable line: non-breaking fixes and additive features only. |
| `2.0` | Next major, where breaking changes go. |

A second backend (R3) is aspirational. It can arrive in any `0.x` or `1.x` release, since adding a
namespace changes nothing about an existing one.

## Essential goals: v0.1.0

### R1 — A development environment and demo to test against

*delivered · advances G1*

A demo project that runs the package the way a real project would, so every page can be looked at
and clicked through while it is being built. It signs in with fixed demo accounts, seeds the data
each page needs, and, given a Stripe sandbox's keys in `demo/.env`, reaches the real provider:
real customers and subscriptions, the real pricing table, the real portal. Without that file it
still runs, on obviously fake values, which is what a fresh clone and CI see.

### R2 — The first backend: drf-stripe-subscription

*delivered in [#6](https://github.com/django-mvp/django-mvp-payments/issues/6), [#16](https://github.com/django-mvp/django-mvp-payments/issues/16), [#24](https://github.com/django-mvp/django-mvp-payments/issues/24), [#25](https://github.com/django-mvp/django-mvp-payments/issues/25), [#37](https://github.com/django-mvp/django-mvp-payments/issues/37) · advances G1, G2*

Everything a subscriber needs, for projects using drf-stripe-subscription, looking like the rest of
their django-mvp site. The pages show a person where they stand. Anything that changes what they
pay is handed to Stripe's own hosted pages.
[ADR 0009](adr/0009-drf-stripe-subscription-is-the-first-backend.md) records why this backend was
chosen first.

**Done when a subscriber can:**

- see their plan, what it costs, how often they pay and the current billing period, in any state
  the backend reports
- choose a plan if they have none, through Stripe's pricing table
- switch plans, cancel, or update their payment details, through Stripe's customer portal
- come back from Stripe and see what they just did, not the state from before it
  ([#37](https://github.com/django-mvp/django-mvp-payments/issues/37))

A project gets all of it by installing the package beside the
backend and mounting its URLs once, with no view, template or menu entry of its own.

## Aspirational goals

### R3 — A second backend

*multi-feature · advances G3*

A second payment backend, in a namespace of its own beside `drf-stripe`. Which one waits for a
project that needs it. The choice would weigh the same thing ADR 0009 weighed: how much the backend
leaves to the provider's hosted pages, and so how little this package has to build.
