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

## 2026-10-22T08:53:26Z · Implementer US1 · T007

Did: acted on the first full verify, which went red on three things. (1) docs/stripe.md sat outside the documentation layout, so it is now docs/how-to/install-the-stripe-app.md, docs/how-to/point-stripe-at-the-webhook.md and docs/reference/stripe-app.md, and the README links all three. (2) tests/test_stripe_fake.py mirrored no source module, so its two classes moved into tests/test_stripe/test_client.py, the module of the client the fake stands under. (3) the docs step named `SubscriptionQuerySet` and `logger` as undocumented public names; the queryset now has an entry on the reference page and the module loggers are private (_logger).
Verified: uv run pytest tests/test_stripe (112 passed); pre-commit clean.
Next: second verify run, then the report.
Watch: later stories add to the reference page rather than to a docs/stripe.md, which no longer exists.

## 2026-10-22T08:58:17Z · Implementer US2 · T008

Did: SubscriptionQuerySet.for_user(user) (none() for anonymous or unsaved users) and .subscribed() (active, trialing). Reference section "Asking whether a user is subscribed" and a how-to for checking in a view.
Verified: uv run pytest tests/test_stripe/test_models.py::TestSubscriptionQuerySet (19 passed). Red first: AttributeError on for_user before the methods existed. Parametrised over every Subscription.Status plus an unknown status.
Next: T009 stripe_sync command.
Watch: Meta.ordering makes .first() the latest period.

## 2026-10-22T08:59:43Z · Implementer US3 · T009

Did: management command stripe_sync with --user (USERNAME_FIELD value). Customers synced in pk order, each by Customer.sync() in its own transaction; a StripeError becomes a CommandError naming how many were synced and the error type only. A name no user has, or a user with no customer, is a CommandError before Stripe is asked. Reference section and a pointer from the webhook how-to.
Verified: uv run pytest tests/test_stripe/test_management (9 passed); pre-commit clean. Red first: Unknown command 'stripe_sync'.
Next: T010 read-only admin.
Watch: the fake answers by path, so tests with several customers use customers Stripe does not have (resource_missing) rather than distinct subscription lists. Command help text is a plain string because mypy rejects a lazy string for BaseCommand.help.

## 2026-10-22T09:02:24Z · Implementer US4 · T010

Did: admin.py with CustomerAdmin and SubscriptionAdmin over a ReadOnlyAdmin base. No add, no change, and delete refused only on the app's own pages (url name starts with the app label), Django's answer elsewhere, so the user admin still cascades. Django drops delete_selected from a list whose has_delete_permission is False, so no get_actions override (the override signature is deprecated in Django 6.1 and 5.2 is supported). SubscriptionAdmin: list_select_related customer__user, status filter, search on username, email, Stripe ids; the status shows as stored when unknown (a choices field would show a dash), the price goes through mvp_payments.money.Money. Reference section "The admin"; tests use tests/urls_with_admin.py since the demo mounts no admin.
Verified: uv run pytest tests/test_stripe/test_admin.py (23 passed) and tests/test_app.py (13 passed). Red first: ImportError-free but every admin URL failed to reverse before admin.py existed. Mutation probes: emptying list_select_related fails the query-count test; making has_delete_permission always False fails the user-admin delete test.
Next: T011 demo webhook forwarding docs.
Watch: the query-count test warms the first request, which fills a per-process cache and adds a query.

## 2026-10-22T09:03:32Z · Implementer US5 · T011

Did: demo/.env.example and the README's demo section document `stripe listen --forward-to localhost:8020/account/billing/stripe/webhook/` (the path is the demo's account/billing/ mount plus stripe/webhook/), the events to forward, and putting the printed whsec_ value into STRIPE_TEST_WEBHOOK_SECRET. Two tests in tests/test_demo.py: the secret comes from the environment when given, and the demo still has a value without one.
Verified: uv run pytest tests/test_demo.py (all passed). The demo settings already read the secret, so the first test passed on first run; probed by mutation: renaming the environment key in demo/settings.py fails it.
Next: T012 secrets and changelog.
Watch: US5 scenario 1 needs a real sandbox and is documented only; the tests show what settings can show.

## 2026-10-22T09:04:48Z · Implementer US5 · T012

Did: tests that the configured secret key and signing secret appear in no admin page (all four of the app's pages), no webhook response body or log record (refused request, Stripe error that quotes a masked key, unset signing secret, handled event), and no stripe_sync error or output. The existing check test already covers messages and hints. CHANGELOG entry under Unreleased/Added. tests/stripe_fake.py gains respond_with_message_echoing. Reference page notes the SDK's own `stripe` logger.
Verified: uv run pytest tests/test_stripe -k KeepsSecretsOut (6 passed). Probe by mutation: logging the error object instead of its type in the webhook fails the webhook test. Finding: the Stripe SDK itself logs the response body at debug and the error message at info on the `stripe` logger, so a real masked key reaches logs through the SDK if that logger is enabled; documented rather than suppressed.
Next: T013 rename leading-underscore names.
Watch: the webhook test asserts the full secrets are absent from every record and the masked echo is absent from the app's own records only, since the SDK's records carry it.
