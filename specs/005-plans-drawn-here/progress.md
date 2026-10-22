# Progress — 005 Show the plans we offer and let only signed-in users buy one

- 2026-10-22 — Sketch approved in round 2. Build started on the feature branch, level with main. Research, plan and tasks written.

## 2026-10-22T16:44:12Z · Implementer US1 · T001

Did: Catalogue (prices, price, clear, timeout) in mvp_payments/stripe/catalogue.py, StripeConfig.catalogue, FakeStripe.respond_with_pages and price_payload, locmem cache in test settings with an autouse clearing fixture, catalogue docs in stripe-app.md.
Verified: uv run pytest tests/test_stripe/test_catalogue.py, 25 passed; pre-commit clean.
Next: T002, PlanChoices reads the catalogue; one frequency helper on CurrentSubscription.
Watch: ordering compares minor-unit amounts across currencies, as the sketch did.

## 2026-10-22T16:46:33Z · Implementer US1 · T002

Did: PlanChoices reads the catalogue through the app registry; CurrentSubscription.frequency_words shared by frequency_display, PlanChoices and the filters; tag and filters with docstrings and top-level imports; stripe_catalogue.py, the ?sketch= branches and the sketch notices in plans.html removed; test_app import scan lists stripe_plans.py and plans_urls.py.
Verified: uv run pytest tests/test_namespaces tests/test_templatetags tests/test_app.py tests/test_stripe, 305 passed, 1 failed (test_declares_exactly_two_pages_with_the_expected_slugs, one of the 26 D4 tests, retired in T003). pre-commit clean.
Next: T003, the public page view, plans_urls, contribution, SubscriptionPageView.plans_url, and the 26 red tests.
Watch: PlansPageView still imports PlanChoices inside get_context_data because stripe_plans imports contributions which imports views.

## 2026-10-22T16:51:05Z · Implementer US1 · T003

Did: PlansPageView without sketch notices, plans_urls.py (payments_plans:stripe-plans, empty without the Stripe app), SubscriptionPageView.plans_url reversing it or None, Page.login_required removed with its dispatch check, demo sidebar entry renamed, demo base.html no longer loads the provider script. Rewrote the red tests per D4: TestPlansPage replaced, the two TestSubscriptionPage tests re-pointed, contribution/URL tests updated, plans-unavailable component test no longer asserts wording.
Verified: uv run pytest tests/test_views.py tests/test_urls.py tests/test_plans_urls.py tests/test_contributions.py tests/test_namespaces tests/test_components/test_stripe.py::TestPlansUnavailable tests/test_app.py, 139 passed. pre-commit clean.
Next: T004, remove the pricing table, sign-in notice, script, customer session method, the two settings, the demo pages; rewrite plans-page.md and the install how-to; CHANGELOG.
Watch: tests/test_demo.py still carries the pricing-table home page test and the two unavailable-state routes, retired in T004.

## 2026-10-22T16:54:27Z · Implementer US1 · T004

Did: removed the pricing table component, sign-in notice, pricing_table.js, Customer.pricing_table_client_secret, the two settings (tests, demo, .env.example), the demo's two pricing-table pages with their routes, views and the landing page sections about them, and their tests. Rewrote docs/reference/plans-page.md; updated the install how-to, stripe-app.md, user-subscriptions-page.md, README, CONTEXT.md, namespaces.md; CHANGELOG entries.
Verified: uv run pytest tests/test_demo.py tests/test_components tests/test_stripe/test_models.py tests/test_views.py tests/test_app.py, 208 passed. pre-commit clean.
Next: the full verify, then the completion report.
Watch: CONSTITUTION.md Articles XI to XIII, ADRs 0010/0012 and specs/003 still describe the old page; the plan puts them in the documentation set for a later story.

## 2026-10-22T17:03:21Z · Implementer US2 · T005

Did: Customer.start_checkout() (customer or email, signed reference, promotion codes; a customer Stripe no longer has is synced away and the session asked for again) and CheckoutView replacing the sketch, with docs/reference/stripe-app.md rewritten.
Verified: uv run pytest tests/test_stripe -q -> 256 passed; pre-commit green.
Next: T006 return view with session_id.
Watch: success_url braces appended after build_absolute_uri.

## 2026-10-22T17:03:52Z · Implementer US2 · T006

Did: BillingReturnView reads session_id; with no customer it ties the purchase via from_checkout (only when the session was made for this person) before syncing. Docs updated.
Verified: uv run pytest tests/test_stripe/test_views.py -k TestBillingReturn -> 9 passed.
Next: T007 buy controls on the cards.
Watch: none.

## 2026-10-22T17:05:15Z · Implementer US2 · T007

Did: tests and docs for the way to buy on each card (sign-in with next back to the plan, checkout form, Manage for a held plan, picked frequency selected, accessible names and description). The approved markup already did this; no template change.
Verified: uv run pytest tests/test_views.py -k TestPlansWayToBuy -> 8 passed. Probed by removing aria-describedby, the anchor, the held branch and return_to from plan_choose.html: each failed a test; template restored.
Next: US2 records, then T008.
Watch: the held badge is not asserted (wording/appearance).

## 2026-10-22T17:06:25Z · Implementer US3 · T008

Did: verified product.* and price.* webhooks and stripe_sync clear the catalogue. Docs: webhook events, cache timeout, shared-cache caveat.
Verified: uv run pytest tests/test_stripe -q -> 270 passed.
Next: US3 records, then T009.
Watch: none.
