# Tasks: Show the plans we offer and let only signed-in users buy one

Ordered and sequential. Test-first wherever there is behaviour. The approved sketch's templates
and copy are kept: a task changes them only to remove a sketch fake. Documentation for a public
name lands in the task that introduces it.

## Phase 1 — US1: a visitor reads the plans on offer (P1)

- [ ] T001 [US1] `mvp_payments/stripe/catalogue.py` `Catalogue` (`prices`, `price`, `clear`,
  `timeout`) and `StripeConfig.catalogue`. A Stripe error caches the unavailable result for 60
  seconds under the same key (`clear()` removes it), so an outage does not hold a worker on every
  request. Extend `FakeStripe` to serve consecutive pages for one path (`has_more` true on all but
  the last). Tests in `tests/test_stripe/test_catalogue.py` against `FakeStripe`: every page
  fetched; filters (inactive product, one-off, metered, tiered, null amount); ordering; second
  call makes no request; `clear()` forces a fetch; a missing secret key returns `None`, makes no
  request and caches nothing; a Stripe error returns `None`, logs no Stripe message, is not
  fetched again within 60 seconds and is fetched after; the timeout setting is honoured.
  Local-memory cache in `tests/settings.py`, cleared by an autouse fixture. Document in
  `docs/reference/stripe-app.md`.
- [ ] T002 [US1] Replace the sketch catalogue: `PlanChoices` reads `StripeConfig.catalogue`;
  delete `namespaces/stripe_catalogue.py` and every `?sketch=` branch. Frequency wording comes
  from one `CurrentSubscription` staticmethod taking interval and count, used by
  `frequency_display`, `PlanChoices` and the filters, with no dummy instance. Tests for
  `PlanChoices` (intervals ordered shortest first, starting frequency, held prices, ready price)
  and the four template filters, including JPY and KWD amounts and an unknown interval. Keep
  `tests/test_app.py`'s import scan reaching the new modules.
- [ ] T003 [US1] Public plans page: `PlansPageView(MVPTemplateView)`, `mvp_payments/plans_urls.py`
  (`payments_plans`, `stripe-plans`, only with the Stripe app installed), the plans `Page` out of
  the contribution, `SubscriptionPageView.plans_url` reversing it or `None`. Remove
  `Page.login_required`, whose only user was the plans page (decisions.md D5). Rewrite or retire
  each of the 26 tests the sketch's route move turned red, as decisions.md D4 lists. Tests: open
  to an anonymous visitor at the mounted address; every price on offer rendered with name,
  amount, frequency, description and features, and nothing for missing ones; no pricing table
  element and no script; unavailable and empty states; product text escaped; not routed without
  the Stripe app; the user subscriptions page links to it, and offers nothing when it is not
  mounted.
- [ ] T004 [US1] Remove the pricing table: `cotton/stripe/pricing_table.html`,
  `sign_in_notice.html`, `static/mvp_payments/stripe/pricing_table.js`,
  `Customer.pricing_table_client_secret()`, the two settings in tests and demo, the demo's two
  pricing-table pages, routes and templates, and their tests. Rewrite
  `docs/reference/plans-page.md` for the page, the parts and the data they receive, and the
  mounting line; update `docs/how-to/install-the-stripe-app.md`; CHANGELOG entries.

## Phase 2 — US2: a visitor buys a plan, signing in first if they need to (P1)

- [ ] T005 [US2] `Customer.start_checkout()` and `CheckoutView` at `stripe/checkout/`. The success
  URL is the absolute return path with `?session_id={CHECKOUT_SESSION_ID}` appended after
  `build_absolute_uri`, so the braces reach Stripe unencoded. The view checks
  `Catalogue.prices() is None` first (error message), and only then treats a missing price as no
  longer on offer. A Stripe customer that Stripe no longer has (`resource_missing`) is synced away
  and the session created again without it. Tests: the session Stripe is asked for carries the
  price, mode, signed reference, existing customer or else the account's email, promotion codes,
  and success and cancel addresses, the success address carrying the literal
  `{CHECKOUT_SESSION_ID}`; anonymous POST goes to sign-in and Stripe is not called; GET refused;
  a price not on offer and a made-up one create nothing and add a warning; the catalogue
  unavailable adds the error message; a held price goes to the user subscriptions page; a Stripe
  error adds an error message and returns; a missing Stripe customer is dropped and checkout is
  still created; an unsafe `return_to` falls back to the plans page.
- [ ] T006 [US2] `BillingReturnView` with `session_id`: whenever `Customer.for_user()` is `None`
  at return, the purchase is tied with `Customer.from_checkout()` and synced before the redirect.
  Tests with `FakeStripe`.
- [ ] T007 [US2] The way to buy on the page: signed-out link to sign-in with `next` back to the
  plan; signed-in form posting to the checkout; held price marked and leading to the user
  subscriptions page, an ended one not marked; the picked price's frequency selected and its
  card's id anchor present (the outline is styling and is not tested); each control's accessible
  name and its description of the off-site checkout. Remove the sketch's inline notice. Document
  in `docs/reference/plans-page.md`.

## Phase 3 — US3: a developer changes the plans in Stripe's dashboard (P2)

- [ ] T008 [US3] `webhook` clears the catalogue on verified `product.*` and `price.*` events;
  an unverified one leaves it. `stripe_sync` clears it. Tests in the existing webhook and
  command test modules. Document the events in `docs/how-to/point-stripe-at-the-webhook.md`, and
  the timeout and clearing in `docs/reference/plans-page.md` and
  `docs/how-to/install-the-stripe-app.md`, stating that webhook and sync clearing reach the page
  only with a cache shared across processes (not local-memory or dummy), and that otherwise
  changes arrive when the catalogue expires.

## Phase 4 — US4: a developer puts the plans on their own pages, their own way (P2)

- [ ] T009 [US4] `{% stripe_plans %}` in a project's own template renders the same plans, and a
  sign-in from there returns to that page. Without the Stripe app installed, `PlanChoices` returns
  `prices` `None` and the parts render nothing (test under `settings_without_stripe_app`). A
  project template overriding `cotton/stripe/plan_features.html` replaces that part on every card
  and leaves the others. A project loop composing the parts replaces one part for one placement.
  Tests use the existing project-template-override settings. Document placing and replacing,
  with examples, in `docs/reference/plans-page.md`.
- [ ] T010 [US4] Demo: file-based cache, offline seed priming the demo catalogue, `/plans/`
  mounted, Plans in the sidebar, the landing section kept. `tests/test_demo.py` updated.
- [ ] T011 [US4] Remove `Page.in_navigation`: the plans page was its only page kept out of the
  navigation, and it has left the contribution (same reasoning as decisions.md D5). Behaviour of
  the remaining pages unchanged; the existing navigation tests stay green.

## Review fixes

- [ ] T012 [US1] CR-001: the plans page tests for "cannot be shown" and "none on offer" check which empty-state component rendered (by a hook, never wording); swapping the two branches in `mvp_payments/stripe/plans.html` turns them red.
- [ ] T013 [US1] CR-003: one billing-length table. `PlanChoices.intervals` reads `Catalogue.BILLING_DAYS` through the app config; `PlanChoices.INTERVAL_DAYS` is deleted.
- [ ] T014 [US1] CR-004: `docs/reference/plans-page.md` and the `Catalogue` docstring say plans are ordered cheapest first within a currency, with no conversion.
- [ ] T015 [US2] CR-005: `Customer.start_checkout` syncs and retries only when the `resource_missing` error names the customer (`error.param == "customer"`). Test: a missing price with a customer present raises and does not ask Stripe for the customer.
- [ ] T016 [US2] CR-006: `docs/reference/user-subscriptions-page.md` says checkout from the plans page already returns through `payments:stripe-billing-return`; the instruction to set a success address stays only for a checkout the project builds itself.
- [ ] T017 [US4] CR-002: the documented one-page loop example carries the checkout note with its id, and the plan-choose entry says the control is described by it. A test of the loop placement asserts the id the control names is on the page.
- [ ] T018 [US4] CR-007: the every-card override test uses two prices and asserts the override's marker once per price.
- [x] T019 [US4] Browser check: the demo catalogue carries the descriptions and features approved in the sketch, not placeholders.
