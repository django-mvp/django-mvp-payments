# ADR 0013 — The plans are drawn from a cached catalogue and bought through a checkout the app starts

**Status:** accepted. Supersedes [ADR 0012](0012-the-plans-page-is-open-to-everyone.md).

## Decision

The plans page draws the plans itself, from the prices and products in the project's Stripe
account, instead of rendering Stripe's pricing table. The Stripe app reads every active recurring
price with its product in one paginated list call and keeps the result, exactly as Stripe returned
it, in the project's default cache. A verified `product.*` or `price.*` webhook clears it, so does
`stripe_sync`, and it expires on its own after `MVP_PAYMENTS["STRIPE_CATALOGUE_TIMEOUT"]` seconds
(an hour by default). No product or price is stored in the database.

Anyone can read the plans. Buying one is a POST to the Stripe app's checkout view, which requires
sign-in, accepts only a price on offer, and creates a Stripe Checkout session carrying the
person's signed reference ([ADR 0011](0011-a-checkout-is-tied-to-its-user-by-a-signed-reference.md))
and their existing Stripe customer. A visitor who is not signed in is sent to sign in first and
comes back to the plan they picked.

## Why

- **The pricing table could not do both.** Its buttons went straight to checkout from inside
  Stripe's own frame, so a visitor who was not signed in could buy a plan tied to no account.
  ADR 0012 kept the plans from such a visitor for that reason. Starting checkout from a view of
  our own that requires sign-in makes a purchase tied to nobody impossible, so the plans can be
  shown to everyone.
- **A cache is enough.** A plans page needs the catalogue to read, not to query. Copying products
  and prices into models would mean keeping two more tables in step with Stripe for no page that
  needs them. The cache holds Stripe's own JSON, so a project that replaces a part of a plan card
  reads Stripe's documented field names.
- **An outage must not take the page down.** A failed read is remembered as unavailable for a
  minute, so a Stripe outage does not hold a worker on every view of a public page.

## What it costs

- Clearing on a webhook or from `stripe_sync` reaches the page only when the project's cache is
  shared between processes. With a per-process cache, changes arrive when the catalogue expires.
- Settings made on a pricing table in Stripe's dashboard no longer apply. Checkout accepts
  promotion codes. Tax collection and trials are not turned on.

## Revisit if

A project needs reports or queries by plan, or has a catalogue too large to fetch in one go. Then
products and prices become models, kept in step through the same webhooks.
