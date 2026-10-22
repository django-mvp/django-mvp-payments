# Progress — FS-004

- 2026-10-22 Specification approved by Sam in session. Branch brought up to date with main (django-mvp 0.30.0). Research, plan and tasks written.

## 2026-10-22T08:43:03Z · Implementer US1 · T001

Did: added the stripe-lite extra (stripe>=16,<17) and moved the dev group onto it; uv sync moved the venv from stripe 7.14 to 16.0.0. The demo no longer mounts drf_stripe.urls and pins the global stripe.api_version to 2020-08-27 in DemoConfig.ready(). tests/test_app.py rewritten: interface rules now skip mvp_payments/stripe/, import scan uses ast, base requirements and the extra's requirements are asserted, and no module outside the app imports the SDK.
Verified: uv run pytest tests/test_app.py tests/test_demo.py (48 passed). New tests were red first (extra missing; demo URLconf import error on stripe.error; api_version unpinned).
Next: T002 app skeleton; the mypy_path check needs mvp_payments/stripe/ to exist, so it is done there.
Watch: deptry DEP002 would flag stripe until the app imports it, so it is ignored temporarily in pyproject.toml; T002 removes the ignore.

## 2026-10-22T08:44:56Z · Implementer US1 · T002

Did: created mvp_payments/stripe/ with apps.py (label mvp_payments_stripe, BigAutoField), client.py (API_VERSION 2026-09-30.endive, client() building StripeClient from MVP_PAYMENTS with no SDK globals, a private _http_client hook the test fixture will set), checks.py (E001, E002; messages name the setting, never a value). Demo INSTALLED_APPS gains the app; demo settings read STRIPE_TEST_SECRET_KEY and STRIPE_TEST_WEBHOOK_SECRET with fake fallbacks; tests/settings.py pins fakes so a developer's demo/.env cannot reach the suite. demo/.env.example documents the webhook secret. Removed the temporary deptry ignore for stripe.
Verified: uv run pytest tests/test_stripe tests/test_app.py (28 passed); uv run mypy clean. ARCH-003 was real: with mypy_path = "mvp_payments/" mypy reported "Source file found twice under different module names: mvp_payments.stripe and stripe". Removed mypy_path; mypy now resolves import stripe to the SDK and passes.
Next: T003 models and migration.
Watch: checks use gettext, not gettext_lazy, because Error's hint is typed str.

## 2026-10-22T08:46:28Z · Implementer US1 · T003

Did: models.py with Customer, Subscription, Subscription.Status and an empty SubscriptionQuerySet; migration 0001_initial; StripeCustomerFactory and StripeSubscriptionFactory in tests/factories.py; docs/stripe.md (install, settings, checks, API version, records) and an install section in the README that links it. The docs directory has no index page, so the README is where its pages are linked.
Verified: uv run pytest tests/test_stripe tests/test_factories.py tests/test_app.py (64 passed). Tests: one parametrised field contract over every field, makemigrations --check, table names, user deletion cascade, one customer per user, several subscriptions, ordering, an unknown status and a JPY amount stored as given.
Next: T004 fake Stripe HTTP client.
Watch: the field-contract test reads field._verbose_name, because Django fills verbose_name in from the field name when none is given.

## 2026-10-22T08:47:29Z · Implementer US1 · T004

Did: tests/stripe_fake.py with FakeStripe (a stripe.HTTPClient subclass keyed by method and path, recording every request with its params, canned lists, canned errors, an unreachable route, and a loud failure for any request nobody canned), payload builders for customer, product, subscription (billing period on the first item, as the sandbox returns it), checkout session and event, and sign_webhook (hmac-sha256 over timestamp.payload). The stripe_fake fixture in conftest.py sets the client module's _http_client hook.
Verified: uv run pytest tests/test_stripe_fake.py (9 passed): SDK parsing, auto-paging, recording, error mapping to InvalidRequestError.code, connection error, uncanned request, and the signed payload passing the real construct_event, failing for another secret and an old timestamp.
Next: T005 Customer.sync().
Watch: the SDK passes the method in lower case, so the fake upper-cases it before routing.

## 2026-10-22T08:49:00Z · Implementer US1 · T005

Did: Customer.sync() in models.py. Atomic; first statement re-reads the customer row with select_for_update(); retrieves the customer (resource_missing or deleted removes the row and its subscriptions); lists subscriptions with status=all and no expansion; fetches each distinct product once for its name; update_or_create by stripe_id from the first item; deletes rows Stripe did not return. Documented under "How records are kept in step" in docs/stripe.md.
Verified: uv run pytest tests/test_stripe (44 passed in test_models.py, 17 of them for sync). Probed by mutation: replacing the final .delete() with .none() fails test_a_row_stripe_no_longer_returns_is_deleted. Red first: all 17 failed with AttributeError before the method existed.
Next: T006 client_reference and from_checkout.
Watch: SQLite has no row locks, so the suite cannot prove FOR UPDATE is emitted. The test asserts the customer SELECT is the first statement in the transaction; the lock itself is by construction.

## 2026-10-22T08:49:59Z · Implementer US1 · T006

Did: Customer.client_reference(user) (pk + "_" + salted_hmac sha256 hexdigest under the app's own salt) and Customer.from_checkout(session_id): retrieves the session, refuses non-subscription mode, missing reference or customer, verifies the signature with constant_time_compare before looking the user up, creates or reuses the user's customer, and logs an error naming both ids for a second customer. One refusal beyond the plan: a customer id already recorded for a different user is also refused and logged, since creating it would hit the unique constraint and make the webhook fail on every retry. Documented in docs/stripe.md.
Verified: uv run pytest tests/test_stripe (77 passed). Red first: 18 new tests failed with AttributeError. Covered: allowed characters, bare pk, tampered signature, another user's signature, deleted user, no reference, no customer, payment and setup modes, same customer reused, second customer, customer owned by someone else, Stripe unreachable.
Next: T007 webhook view and URLs.
Watch: salted_hmac is given algorithm="sha256" explicitly; the default warns of a change in Django 2028.

## 2026-10-22T08:52:02Z · Implementer US1 · T007

Did: views.webhook (csrf_exempt, require_POST function view), urls.py (stripe/webhook/, name stripe-webhook), and mvp_payments/urls.py includes the app's URLs when apps.is_installed("mvp_payments.stripe"). Signature verified with stripe.Webhook.construct_event before anything is read: ValueError or SignatureVerificationError gives 400. checkout.session.completed goes through Customer.from_checkout, customer.subscription.* and customer.deleted find the Customer by stripe_id, then sync(). The handling runs in one transaction.atomic so a StripeError (500) leaves no half-recorded customer. An unset or empty STRIPE_WEBHOOK_SECRET answers 500 and verifies nothing, because an empty key lets anyone sign. Bodies are empty in every case; only the error type is logged. docs/stripe.md gains the webhook address, events to send and answers.
Verified: uv run pytest tests/test_stripe tests/test_urls.py tests/test_app.py (121 passed). Mutation probe: swapping construct_event for construct_event_without_verification failed 5 verification tests. The address-absent case runs in a fresh process under tests/settings_without_stripe_app.py.
Next: full verify and the report.
Watch: the logger call keeps the error type only and carries a noqa for TRY400, since a StripeError message can echo part of the key.
