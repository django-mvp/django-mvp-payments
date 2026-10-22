# Tasks: Keep each user's Stripe subscription in the project's own database

Ordered, and run one after another: several stories edit `models.py` and the Stripe app's reference page, so
no two run in parallel. Each task is test-first where it has behaviour. Documentation for a public name lands in
the task that introduces it, in `docs/reference/stripe-app.md` (and a how-to under `docs/how-to/` where it is a task a developer performs).

## Phase 1 — Foundational

- [ ] T001 Add the `stripe-lite` extra (`stripe>=16,<17`) and move the dev group onto it in place
  of `stripe<8`. Stop the demo mounting `drf_stripe.urls` and pin the global `stripe.api_version`
  for the demo's drf-stripe calls. Rewrite `tests/test_app.py` so the interface rules exclude
  `mvp_payments/stripe/` and assert the base requirements, the extra's requirements, and that no
  module outside the app imports `stripe`. Check that mypy resolves `import stripe` to the SDK
and not to `mvp_payments/stripe/` under the current `mypy_path`, and fix `mypy_path` if not.
Suite green on stripe 16.
- [ ] T002 Create `mvp_payments/stripe/` with `apps.py` (label `mvp_payments_stripe`), `client.py`
  (`API_VERSION`, `client()`), and `checks.py` (E001, E002). `StripeConfig` sets
  `default_auto_field`. Add the app to the demo's `INSTALLED_APPS`, and give the demo settings
  its secret key and webhook secret from `demo/.env` with obviously fake fallbacks, so the demo
  passes its checks from this task on. Tests: the checks fire
  for each missing setting and name no value; `client()` uses the configured key and
  `API_VERSION`.
- [ ] T003 `models.py`: `Customer`, `Subscription`, `Subscription.Status`, `SubscriptionQuerySet`
  with no methods yet; migration `0001_initial`; factories. Tests: every field has `verbose_name`
  and `help_text`; `makemigrations --check` clean; the tables carry the `mvp_payments_stripe`
  label; deleting a user removes their customer and subscriptions. Start `docs/stripe.md` (install, settings, migrate) and add it to the docs index and the
  README's install steps.
- [ ] T004 `tests/stripe_fake.py`, the fake HTTP client and its fixture, and a signing helper for
  webhook payloads. Tests in `tests/test_stripe_fake.py` for the fake itself only where it holds
  logic.

## Phase 2 — US1: keep subscriptions in step (P1)

- [ ] T005 `Customer.sync()`: fetch customer and subscriptions, upsert, delete what Stripe no
  longer returns, delete the customer when Stripe has none. Tests: every field recorded from the
  first item, with the product name from a separate product fetch; a change followed; deleted and
  missing customer; repeat leaves the same rows; a zero-decimal currency stored as reported; an
  unknown status stored.
- [ ] T006 `Customer.client_reference()` and `Customer.from_checkout()`. Tests: the reference uses
  only letters, digits and underscores; ties a new customer from a valid reference; reuses the
  same one; refuses a bare primary key, a tampered or another user's signature, and a session
  with no reference, no customer, not subscription mode, or an unknown user; logs and
  refuses a second customer for a user.
- [ ] T007 `views.webhook` and `urls.py`; `mvp_payments/urls.py` includes it when the app is
  installed. Tests: bad, missing and expired signatures change nothing and get 400; each handled
  event type syncs; out-of-order and repeated deliveries leave the same rows; unhandled types and
  unknown customers get 200; a `StripeError` gets 500 and changes nothing; GET is refused; with
  the app absent from `INSTALLED_APPS` the webhook address does not resolve. Docs:
  the webhook address and which events to send.

## Phase 3 — US2: ask whether a user is subscribed (P1)

- [ ] T008 `SubscriptionQuerySet.for_user()` and `.subscribed()`. Tests: parametrised over every
  status; several subscriptions; none; anonymous. Docs: both answers with examples.

## Phase 4 — US3: re-sync after missed webhooks (P2)

- [ ] T009 `stripe_sync` command. Tests: all customers synced; `--user` syncs one; unknown user is
  an error; second run changes nothing; a `StripeError` part-way keeps what was synced and fails
  with the count. Docs.

## Phase 5 — US4: read-only admin (P2)

- [ ] T010 `admin.py`. Tests: a superuser can list, filter and search but gets no add, change or
  delete on the app's pages; a superuser can still delete a user who has a customer from the user
  admin; the subscription list runs the same number of queries for one row and several; a staff user without view permission sees nothing; the change view shows the record's
  values. Docs.

## Phase 6 — US5: webhooks in the demo (P3)

- [ ] T011 `demo/.env.example` and the README's
  demo section document `stripe listen`. Test: the demo's settings carry the webhook secret from
  the environment when given.

## Phase 7 — Cross-cutting

- [ ] T012 Secrets appear in no admin page, check message, webhook response or log record
  (SC-008). CHANGELOG entry.
- [ ] T013 Rename the leading-underscore names the app introduced (`_http_client`, `_customer_for`,
  `_REQUIRED`, `_REFERENCE_SALT`, `_signature`, `_from_epoch`, `_logger`) to plain names. The
  repository's convention is no leading underscores. Behaviour unchanged, so no new tests.
