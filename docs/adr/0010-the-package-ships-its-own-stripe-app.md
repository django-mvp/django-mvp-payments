# ADR 0010 — The package ships its own Stripe app

**Status:** accepted. Supersedes [ADR 0009](0009-drf-stripe-subscription-is-the-first-backend.md).

## Decision

The package keeps its own subscription records for Stripe, in an app of its own,
`mvp_payments.stripe`. A project installs `django-mvp-payments[stripe-lite]` and adds the app to
`INSTALLED_APPS`. drf-stripe-subscription stops being a supported backend, and the `drf-stripe`
namespace is replaced by `stripe`.

The app keeps the least it can: who each user's Stripe customer is, and that customer's
subscription with its status, price and period. It learns about changes from Stripe's webhooks
and from Stripe directly when a reader comes back from a hosted page. Products and prices are not
copied, because the plans page uses Stripe's own pricing table. Choosing, switching and cancelling
a plan, and updating payment details, stay on Stripe's hosted pages, as they were under ADR 0009.

## Why

drf-stripe-subscription was chosen because it kept local records and left everything else to
Stripe's hosted pages. Building on it showed what that costs:

- **It has stopped moving.** Its last release was 1.2.2, in November 2024. It imports
  `stripe.error`, which the stripe SDK removed at version 8, so a project using it is held on
  stripe 7 while the SDK is at 16.
- **It brings Django REST Framework and pydantic** into every project that uses it, for a handful
  of endpoints.
- **Its parts we needed most do not work.** Its billing-portal endpoint raises for anybody who has
  used it before, and it has no endpoint for Stripe's plan-change screen. The demo already mounts
  its own portal, plan-change and return views, so most of what a backend does here was being
  written anyway, outside the package and without the tests it needs.

dj-stripe is maintained, but it copies most of Stripe's object model into the project's database.
That is far more than a small project needs to show a person their subscription, and it also pins
the SDK below the current release.

What is left to build is small: two records, a webhook endpoint and the views that hand a reader
to Stripe and bring them back. Written here, it can be designed for these pages and tested
properly, on the current SDK, with no dependency beyond Stripe's own library.

The install option is called `stripe-lite` rather than `stripe` so that nobody reads it as
support for a fuller Stripe integration such as dj-stripe. The app's Django label is
`mvp_payments_stripe`, so it cannot collide with another app called `stripe`.

## What it costs

- **We own the webhook handling.** It is the most security-sensitive code in the package.
  Article XI sets how it behaves: the signature is checked before anything is read, and an event
  prompts a fetch from Stripe instead of being trusted, so late, repeated and out-of-order events
  are harmless.
- **We follow Stripe's API versions ourselves.** The app pins the version it is written against
  (Article XVI).
- **Scope has to be held.** Taxes, invoice lists, metered billing, one-off payments and billing
  for teams are each a reason to grow the app, and none of them is needed to show a person where
  they stand.
- **The `drf-stripe` work is replaced.** The pages, components and specifications carry over to
  the new app. The code that read drf-stripe-subscription's records, and the demo's workaround
  views, are removed.

## Revisit if

A project needs something from Stripe this app's records cannot hold, or the webhook handling
grows past a page of code. Either is a sign the app is turning into a Stripe integration, which
is what this decision chose not to build.
