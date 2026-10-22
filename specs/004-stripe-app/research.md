# Research — FS-004

Against main at `1936e87` (django-mvp 0.30.0), stripe-python 16.0.0, Stripe API `2026-09-30.endive`.

## Planning notes

### Stay simple but effective — adopted

The design follows the shape most write-ups of "Stripe subscriptions in your own Django models"
settle on, with nothing added: one customer row per user, one row per subscription, one webhook
view that verifies the signature and re-fetches from Stripe, and a sync command that runs the
same code. Where a write-up adds more (a copy of products and prices, an event log table, a
generic event dispatcher, background tasks), this plan leaves it out:

- **No product or price tables.** The pricing table is Stripe's own (FS-003). The subscription
  row carries the price's identifier, amount, currency, interval and product name, which is
  everything the subscription page shows.
- **No event log and no idempotency table.** Every event is answered by fetching the customer's
  current subscriptions from Stripe and writing what comes back. Applying that twice, late or out
  of order leaves the same rows, so there is nothing to deduplicate.
- **One code path.** The webhook view and the sync command both call `Customer.sync()`. The only
  thing the webhook adds is tying a new customer to the user who checked out.
- **No background queue.** Stripe allows 20 seconds for a webhook response. A sync is two API
  calls for one customer, well inside that.

## Findings that shape the design

1. **The billing period is on the subscription item, not the subscription.** In API versions
   from 2025-03-31 onwards `current_period_start` and `current_period_end` live on each item
   (`stripe/_subscription_item.py` in 16.0.0, and absent from `_subscription.py`). The app reads
   them from the subscription's first item, together with that item's price.
2. **The SDK pins its own API version.** `stripe._api_version._ApiVersion.CURRENT` is
   `2026-09-30.endive` in 16.0.0, and `StripeClient` sends it unless told otherwise. The app
   states the version as a constant and passes it to `StripeClient(..., stripe_version=...)`
   (FR-011, Article XVI), and the extra pins `stripe>=16,<17` so the constant and the SDK's
   object shapes move together.
3. **Signature verification is the SDK's.** `stripe.Webhook.construct_event(payload, header,
   secret, tolerance=300)` verifies the `Stripe-Signature` header and raises
   `SignatureVerificationError`. Nothing of ours reimplements it.
4. **The checkout carries the user.** A checkout session's `client_reference_id` is a value of
   the project's choosing, set by the pricing table's `client-reference-id` attribute and returned
   on the completed session. The app writes the user's primary key there and reads it back from
   the session it fetches from Stripe, never from the event body. Setting the attribute on the
   pricing table belongs to the work that moves the pages; until then nothing on our pages sends
   it and the app ties nobody, which is the safe failure.
5. **drf-stripe-subscription runs on stripe 16 once its URLconf is not mounted.** Its only
   import of the removed `stripe.error` module is in `drf_stripe/serializers.py`, reached from
   its views. With the demo no longer mounting `drf_stripe.urls` (the demo's own portal view is
   what the page already uses), the whole suite passed on stripe 16.0.0: 196 tests, checked on
   this branch on 2026-10-22. So the dev environment moves to stripe 16 in this feature and the
   `drf-stripe` pages keep working until they move. The demo's own drf-stripe calls use the SDK's
   global configuration, so the demo pins `stripe.api_version` to the version drf-stripe's models
   parse, the last one with the billing period on the subscription (`2025-02-24.acacia`), for those calls. The app never uses the global configuration, so the two
   cannot interfere.
6. **Deleted objects.** Retrieving a deleted customer returns an object with `deleted: true`.
   A customer that never existed raises `InvalidRequestError` with code `resource_missing`. Both
   mean "Stripe no longer has it". Cancelled subscriptions stay retrievable and are listed by
   `subscriptions.list(customer=..., status="all")`.
7. **Events worth handling.** `checkout.session.completed` (a new customer to tie),
   `customer.subscription.*` (created, updated, deleted, paused, resumed, trial_will_end and any
   added later) and `customer.deleted`. Everything else is acknowledged with 200 and ignored.
   The handling reads only the identifiers from the event: the customer's id, or the checkout
   session's id.

## Decisions

- **Settings.** `MVP_PAYMENTS["STRIPE_SECRET_KEY"]` and `MVP_PAYMENTS["STRIPE_WEBHOOK_SECRET"]`,
  in the settings dictionary the package already reads. Missing either is a system-check error
  (`mvp_payments_stripe.E001`, `E002`), which is what makes a misconfiguration visible at
  `runserver` and `check --deploy` rather than at the first webhook.
- **Webhook URL.** `mvp_payments.urls` includes `mvp_payments.stripe.urls` when the app is
  installed, so the one include line a project already has also mounts the webhook
  (Article XIII). URL name `payments:stripe-webhook`, path `stripe/webhook/` under wherever the
  project mounted the package.
- **A second Stripe customer for a user who already has one.** The completed checkout is logged
  as an error naming both customer identifiers and nothing is changed. It can only happen when a
  checkout is started without the existing customer, which the work moving the pages prevents by
  passing the customer to the pricing table. Replacing the customer silently would orphan the
  first one's subscriptions.
- **Multi-item subscriptions.** The first item's price and period are recorded. The pricing table
  creates single-item subscriptions, and a project that builds multi-item ones has outgrown this
  app (ADR 0010, "Revisit if").
- **Statuses.** Stored as Stripe's own strings in a `CharField` with Stripe's documented
  statuses as `choices`, so the admin can filter by them and an unknown one is still stored
  (`choices` are not enforced on save).
- **What counts as subscribed.** `status in {"active", "trialing"}`. A subscription set to cancel
  at period end stays `active` on Stripe until the period ends, so it needs no rule of its own.

## What already exists

| New piece | Where the search stopped |
|---|---|
| Signature verification | Installed package: `stripe.Webhook.construct_event` |
| HTTP calls to Stripe, retries, API version header | Installed package: `stripe.StripeClient` |
| Read-only admin | Django: `ModelAdmin.has_add/change/delete_permission` |
| "Is this user subscribed" | Django: a `QuerySet` method (`for_user()`, `subscribed()`), per the Django standards, section 3 |
| Sync for one customer | New code: `Customer.sync()`, the one operation every path calls |
| Tying a checkout to a user | New code: `Customer.from_checkout()` |
| Webhook endpoint | New code: one function view, `csrf_exempt` and `require_POST` from Django |
| Sync command | Django: a management command calling `Customer.sync()` |
| Configuration checks | Django: the system check framework |
| Amount display | This repo: `mvp_payments.money.Money`, used when the pages move; the app stores the minor unit and currency only |
| Test doubles for Stripe | New code: a fake `stripe.HTTPClient` in `tests/`, so the SDK's own request and response handling runs in tests and only the network is replaced |
| Webhook signatures in tests | Standard library: `hmac` over `"{timestamp}.{payload}"`, as Stripe documents |
