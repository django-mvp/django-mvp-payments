# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.1.1] - 2026-10-28

### Added

- **`mvp_payments.stripe.personal_data`, the Stripe app's records as django-mvp-compliance
  kinds.** A project that lists `StripeCustomer` and `StripeSubscriptions` in
  `MVP_COMPLIANCE_PERSONAL_DATA` gets a person's Stripe customer and subscriptions in their copy
  of their data. Nothing imports the module unless a project names it, so django-mvp-compliance
  stays optional.
- **`Customer.erase()`** deletes a customer at Stripe, which cancels its subscriptions, and then
  deletes its records here.

### Fixed

- **Deleting an account through django-mvp-compliance no longer leaves the person being billed
  (#75).** With the kinds declared, deleting the account deletes the Stripe customer, cancelling
  its subscriptions at once. When Stripe cannot be reached or refuses, the deletion fails as a
  whole and nothing is removed.

## [v0.1.0] - 2026-10-23

The first release. Nothing was published before it, so everything below is new.

### Added

- **Payment pages for django-mvp projects, one namespace per payment backend.** Installing the
  package alone changes nothing a person sees. Adding a backend's app to `INSTALLED_APPS` makes its
  pages appear in django-mvp's Account Center, with a navigation entry under a Billing group and a
  card on the overview. A project includes the package's URLs once:
  `path("account/billing/", include("mvp_payments.urls"))`, before django-mvp's own include, with
  `mvp_payments` listed before `mvp` in `INSTALLED_APPS`. `docs/namespaces.md` explains how a
  namespace is declared and how a second one would be added without touching the first.
- **`mvp_payments.stripe`, the Stripe app.** Installed with the `stripe-lite` extra
  (`stripe>=16,<17`) and turned on by adding it to `INSTALLED_APPS`. It keeps each user's Stripe
  customer and every subscription Stripe reports for them in your database, against Stripe API
  version `2026-09-30.endive` whatever your account's default is. It needs
  `MVP_PAYMENTS["STRIPE_SECRET_KEY"]` and `MVP_PAYMENTS["STRIPE_WEBHOOK_SECRET"]`, and a system
  check names whichever is missing without printing it. Another warns when the default cache is
  Django's dummy cache, which would send every view of the plans page to Stripe.
  - Its webhook, `payments:stripe-webhook`, verifies every event and then fetches the current state
    from Stripe, so late, repeated and out-of-order events leave the same records.
  - A purchase is tied to the user who made it by a signed reference carried through checkout, never
    by email address. A reference signed before `SECRET_KEY` was rotated still verifies while the old
    key is in `SECRET_KEY_FALLBACKS`.
  - Every checkout is for the person's own Stripe customer, made before their first one, so buying
    twice can never leave a paid subscription on a customer the site does not know.
  - `Subscription.objects.for_user(user).subscribed()` answers whether someone is subscribed, for
    your own views.
  - `python manage.py stripe_sync` re-syncs every recorded customer, or one with `--user`, after
    missed webhooks.
  - Customers and subscriptions appear in the admin, read-only for everyone, a superuser included.
  - A request to Stripe gives up after `MVP_PAYMENTS["STRIPE_TIMEOUT"]` seconds, ten by default,
    and is tried twice more when it times out or Stripe fails.
  - One person may start ten checkouts, and open the billing portal ten times, in a minute.
- **The user subscriptions page**, signed-in only. It lists every subscription the person currently
  holds, with its status, plan, amount, billing frequency and current period, and offers "Manage
  subscription" (Stripe's billing portal) and "Switch plans" (Stripe's plan-change screen). Coming
  back from Stripe, the page shows what just changed, and polls briefly while the webhook catches
  up. The way back asks Stripe at most once every ten seconds for each person. Components: `<c-stripe.subscription>`, `<c-stripe.amount>`, `<c-stripe.portal-link>`,
  `<c-stripe.plans-link>`, `<c-stripe.no-subscription>` and `<c-stripe.provider-return>`, with
  `billing_portal.js` binding the two controls.
- **The plans page**, public. It draws every active recurring price in your Stripe account with its
  product's name, description and features, behind a monthly and yearly switch, and says plainly
  when Stripe cannot be reached or has nothing on offer. Anyone can read it. Only a signed-in person
  can buy: "Choose" starts a Stripe Checkout session for their account through
  `payments:stripe-checkout`, and a visitor who is not signed in is sent to sign in and brought back
  to the plan they picked. It has an address of its own, mounted with a second include,
  `path("plans/", include("mvp_payments.plans_urls"))`, as `payments_plans:stripe-plans`.
  - The plans are read from Stripe and kept in your project's cache, cleared by product and price
    webhooks and by `stripe_sync`, and expiring after `MVP_PAYMENTS["STRIPE_CATALOGUE_TIMEOUT"]`
    seconds (an hour by default).
  - `{% stripe_plans as plans %}` puts the same plans in any template. The page is built from
    `<c-stripe.plans>`, `<c-stripe.plan-card>`, `<c-stripe.plan-price>`, `<c-stripe.plan-features>`,
    `<c-stripe.plan-choose>`, `<c-stripe.no-plans>` and `<c-stripe.plans-unavailable>`, each of which
    a project can replace on its own.
- Every amount is shown in its own currency's unit, zero-decimal and three-decimal currencies
  included, and formatted under the active locale.
- Reference pages for the Stripe app, the user subscriptions page and the plans page, and how-to
  guides for installing the Stripe app, pointing Stripe at the webhook and checking whether a user
  is subscribed.
- A demo project that runs offline on sample data, or against a Stripe sandbox given its keys in
  `demo/.env`.
- Supports Python 3.12 and 3.13, Django 5.2, 6.0 and 6.1, and django-mvp 0.30.0 or later.
