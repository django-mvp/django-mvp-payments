# Roadmap — django-mvp-payments

**Date:** 2026-11-08

This document was designed against [GOALS.md](../GOALS.md). See also [CONTEXT.md](../CONTEXT.md)
for domain terminology and [CONSTITUTION.md](../CONSTITUTION.md) for project standards.

The roadmap is deliberately short. It says which providers are supported and in what order, and
which ways of paying go beyond one person's own subscription, not which pages each one gets. What a provider's pages need to do is decided by the projects that use
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
namespace changes nothing about an existing one. Organisations' places (R4) and referrals (R5) are
aspirational too, and start only once R2 is delivered and running in a project.

## Essential goals: v0.1.0

### R1 — A development environment and demo to test against

*delivered · advances G1*

A demo project that runs the package the way a real project would, so every page can be looked at
and clicked through while it is being built. It signs in with fixed demo accounts, seeds the data
each page needs, and, given a Stripe sandbox's keys in `demo/.env`, reaches the real provider:
real customers and subscriptions, the real catalogue and checkout, the real portal. Without that file it
still runs, on obviously fake values, which is what a fresh clone and CI see.

### R2 — The first backend: the package's own Stripe app

*delivered in [#6](https://github.com/django-mvp/django-mvp-payments/issues/6), [#16](https://github.com/django-mvp/django-mvp-payments/issues/16), [#24](https://github.com/django-mvp/django-mvp-payments/issues/24), [#25](https://github.com/django-mvp/django-mvp-payments/issues/25), [#37](https://github.com/django-mvp/django-mvp-payments/issues/37), [#52](https://github.com/django-mvp/django-mvp-payments/issues/52), [#61](https://github.com/django-mvp/django-mvp-payments/issues/61) · advances G1, G2*

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

### R4 — Places an organisation pays for

*multi-feature · advances G4*

An organisation pays once for a number of places and gives them to its members: a family sharing
one plan, a school paying for its students. The places are the quantity on the organisation's own
Stripe subscription, which is bought and changed on Stripe's checkout and portal like any other
([ADR 0016](adr/0016-an-organisations-places-are-its-subscriptions-quantity.md)). Organisations
come from django-organizations, presented by django-mvp-accounts, and none of this appears in a
project without them.

**Done when:**

- an organisation's owner can buy places, and add or remove places, on Stripe's own pages
- its owner and admins can see who holds each place, give a free one to a member and take one
  back
- the organisation can hand out a code that gives whoever uses it a free place, and a discount
  code works through Stripe's own promotion codes at checkout
- a developer asking whether a person is subscribed gets yes for someone holding a place

Joining an organisation without a place is an invitation, which is django-mvp-accounts'.

### R5 — Referrals

*feature · advances G5*

A person has a referral link to share. A friend who comes through it gets a discount, as a Stripe
promotion code at checkout, and the host project is told when the friend first subscribes, so it
can reward the referrer however it chooses. Who came through whose link is recorded by
pinax-referrals. The package never credits anyone itself
([ADR 0017](adr/0017-the-package-records-referrals-and-the-project-rewards-them.md)).
