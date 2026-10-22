# Tasks: Show the plans we offer and let only signed-in users buy one

Ordered and sequential. Test-first wherever there is behaviour. The approved sketch's templates
and copy are kept: a task changes them only to remove a sketch fake. Documentation for a public
name lands in the task that introduces it.

## Phase 1 — US1: a visitor reads the plans on offer (P1)

- [ ] T001 [US1] `mvp_payments/stripe/catalogue.py` `Catalogue` (`prices`, `price`, `clear`,
  `timeout`) and `StripeConfig.catalogue`. Tests in `tests/test_stripe/test_catalogue.py` against
  `FakeStripe`: every page fetched; filters (inactive product, one-off, metered, tiered, null
  amount); ordering; second call makes no request; `clear()` forces a fetch; missing secret key and
  Stripe error return `None`, cache nothing and log no Stripe message; the timeout setting is
  honoured. Local-memory cache in `tests/settings.py`, cleared by an autouse fixture. Document in
  `docs/reference/stripe-app.md`.
- [ ] T002 [US1] Replace the sketch catalogue: `PlanChoices` reads `StripeConfig.catalogue`;
  delete `namespaces/stripe_catalogue.py` and every `?sketch=` branch. Tests for `PlanChoices`
  (intervals ordered shortest first, starting frequency, held prices, ready price) and the four
  template filters, including JPY and KWD amounts and an unknown interval. Keep `tests/test_app.py`'s
  import scan reaching the new modules.
- [ ] T003 [US1] Public plans page: `PlansPageView(MVPTemplateView)`, `mvp_payments/plans_urls.py`
  (`payments_plans`, `stripe-plans`, only with the Stripe app installed), the plans `Page` out of
  the contribution, `SubscriptionPageView.plans_url` reversing it or `None`. Tests: open to an
  anonymous visitor at the mounted address; every price on offer rendered with name, amount,
  frequency, description and features, and nothing for missing ones; no pricing table element and
  no script; unavailable and empty states; product text escaped; not routed without the Stripe
  app; the user subscriptions page links to it, and offers nothing when it is not mounted.
- [ ] T004 [US1] Remove the pricing table: `cotton/stripe/pricing_table.html`,
  `sign_in_notice.html`, `static/mvp_payments/stripe/pricing_table.js`,
  `Customer.pricing_table_client_secret()`, the two settings in tests and demo, the demo's two
  pricing-table pages, routes and templates, and their tests. Rewrite
  `docs/reference/plans-page.md` for the page, the parts and the data they receive, and the
  mounting line; update `docs/how-to/install-the-stripe-app.md`; CHANGELOG entries.

## Phase 2 — US2: a visitor buys a plan, signing in first if they need to (P1)

- [ ] T005 [US2] `Customer.start_checkout()` and `CheckoutView` at `stripe/checkout/`. Tests: the
  session Stripe is asked for carries the price, mode, signed reference, existing customer or
  else the account's email, promotion codes, success and cancel addresses; anonymous POST goes to
  sign-in and Stripe is not called; GET refused; a price not on offer and a made-up one create
  nothing and add a warning; a held price goes to the user subscriptions page; a Stripe error adds
  an error message and returns; an unsafe `return_to` falls back to the plans page.
- [ ] T006 [US2] `BillingReturnView` with `session_id`: a first purchase is tied with
  `Customer.from_checkout()` and synced before the redirect. Tests with `FakeStripe`.
- [ ] T007 [US2] The way to buy on the page: signed-out link to sign-in with `next` back to the
  plan; signed-in form posting to the checkout; held price marked and leading to the user
  subscriptions page, an ended one not marked; the picked price outlined and its frequency
  selected; each control's accessible name and its description of the off-site checkout. Remove
  the sketch's inline notice. Document in `docs/reference/plans-page.md`.

## Phase 3 — US3: a developer changes the plans in Stripe's dashboard (P2)

- [ ] T008 [US3] `webhook` clears the catalogue on verified `product.*` and `price.*` events;
  an unverified one leaves it. `stripe_sync` clears it. Tests in the existing webhook and
  command test modules. Document the events in `docs/how-to/point-stripe-at-the-webhook.md` and
  the timeout and clearing in `docs/reference/plans-page.md`.

## Phase 4 — US4: a developer puts the plans on their own pages, their own way (P2)

- [ ] T009 [US4] `{% stripe_plans %}` in a project's own template renders the same plans, and a
  sign-in from there returns to that page. A project template overriding
  `cotton/stripe/plan_features.html` replaces that part on every card and leaves the others. A
  project loop composing the parts replaces one part for one placement. Tests use the existing
  project-template-override settings. Document placing and replacing, with examples, in
  `docs/reference/plans-page.md`.
- [ ] T010 [US4] Demo: file-based cache, offline seed priming the demo catalogue, `/plans/`
  mounted, Plans in the sidebar, the landing section kept. `tests/test_demo.py` updated.
