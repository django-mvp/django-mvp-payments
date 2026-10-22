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
