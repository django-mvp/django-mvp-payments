# ADR 0009 — drf-stripe-subscription is the first backend supported

**Status:** accepted

## Decision

The first payment backend this package supports is
[drf-stripe-subscription](https://github.com/oscarychen/drf-stripe-subscription), in the
`drf-stripe` namespace. A second backend is wanted but not planned, and which one waits for a
project that needs it.

## Why

It needs the least from this package. drf-stripe-subscription keeps a local copy of the provider's
products, prices and subscriptions, so a page can show a person where they stand by reading
records the backend already keeps. Everything that changes what they pay is done on Stripe's own
hosted pages:

- choosing a plan, through Stripe's pricing table and checkout
- switching plans, cancelling and updating a card, through Stripe's customer portal

So the package renders state and hands off, which is all Article XII lets it do. It never holds a
card, takes a payment or decides what anyone is charged, and none of that has to be rebuilt here.

A backend that expects the application to build its own checkout, plan-change or cancellation
screens would need all of that written and maintained in this package. It would also pull the
package toward owning payment logic, which Article XII rules out.

## What it costs

The backend has defects a project meets through our pages, and we do not control its releases.
Two are known:

- Its billing-portal endpoint raises for anybody who has used it before. The demo mounts an
  endpoint of its own instead, and `docs/subscription-page.md` tells a project how to do the same.
- On Python 3.12 and later its synchronisation stores a billing frequency as
  `RecurringInterval.MONTH_1` rather than `month_1`. The package reads both.

The backend also ships no endpoint for the provider's plan-change screen, so a project mounts one
(ADR 0008).

## Revisit if

The backend stops being maintained, or a project needs a backend this one cannot stand in for. A
second backend arrives as a namespace of its own beside this one (Article XV), not as a
replacement for it.
