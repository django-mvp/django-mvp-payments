# Roadmap — django-mvp-payments

**Date:** 2026-10-20

This document was designed against [GOALS.md](../GOALS.md). See also [CONTEXT.md](../CONTEXT.md)
for domain terminology and [CONSTITUTION.md](../CONSTITUTION.md) for project standards.

The roadmap is deliberately short. It says which providers are supported and in what order, not
which pages each one gets. What a provider's pages need to do is decided by the projects that use
them, and is tracked as issues rather than planned here in advance.

## Versioning

| Version | Gate |
|---|---|
| `0.0.x` | Building toward the first backend. Pre-viable, expect churn, nothing published. |
| `0.1.0` | R1 and R2 delivered: Stripe fully supported by the package's own app. The first publish. |
| `0.x` | Fixes and additions that projects using the package ask for. |
| `1.0.0` | The package's settings, components and context names have held steady through at least one real project using it. |
| `1.x` | Stable line: non-breaking fixes and additive changes only. |
| `2.0` | Next major, where breaking changes go. |

A second provider (R3) is aspirational. It can arrive in any `0.x` or `1.x` release, since adding a
namespace changes nothing about an existing one.

## Essential goals: v0.1.0

### R1 — A development environment and demo to test against

*delivered · advances G1*

A demo project that runs the package the way a real project would, so every page can be looked at
and clicked through while it is being built. It signs in with fixed demo accounts, seeds the data
each page needs, and, given a Stripe sandbox's keys in `demo/.env`, reaches the real provider:
real customers and subscriptions, the real catalogue and checkout, the real portal. Without that file it
still runs, on obviously fake values, which is what a fresh clone and CI see.

### R2 — The first backend: the package's own Stripe app

*advances G1, G2*

Everything a subscriber needs, for projects using Stripe, looking like the rest of their
django-mvp site, with the records behind it kept by `mvp_payments.stripe`.
[ADR 0010](adr/0010-the-package-ships-its-own-stripe-app.md) records why the package keeps them
itself rather than relying on a third-party package. The pages show a person where they stand.
Anything that changes what they pay is handed to Stripe's own hosted pages.

**Done when a developer can:**

- install `django-mvp-payments[stripe-lite]`, add `mvp_payments.stripe` to `INSTALLED_APPS`,
  configure their Stripe keys and mount the URLs, with no view, template or menu entry of their
  own
- point Stripe's webhooks at the app and have each user's subscription kept in step with Stripe
- ask, in their own views, whether a user is subscribed

**And a subscriber can:**

- see every plan they hold, what it costs, how often they pay and the current billing period
- read the plans on offer, signed in or not, and buy one once signed in, with the purchase tied
  to them
- switch plans, cancel, or update their payment details, through Stripe's customer portal
- come back from Stripe and see what they just did, not the state from before it

## Aspirational goals

### R3 — A second provider

*multi-feature · advances G3*

A second payment provider, in a namespace of its own beside `stripe`. Which one waits for a
project that needs it. It arrives as another provider app inside this package, or as a
third-party package that ships its own templates built from this package's components. The
choice weighs what ADR 0010 weighed: how much the provider leaves to its own hosted pages, and so
how little has to be built and kept here.
