# Plan — 005 Show the plans we offer and let only signed-in users buy one

**Spec:** `spec.md` (approved) · **Research:** `research.md` · **Sketch:** `sketch.md` (approved, round 2)

## Summary

The Stripe app reads the catalogue from Stripe and caches it, starts checkouts for signed-in
users, and clears the cache on product and price webhooks and on sync. The interface draws the
plans from that catalogue with the Cotton parts approved in the sketch, on a public page with its
own URLconf and in any template through `{% stripe_plans %}`. The pricing table and everything
that served it is removed.

## Technical context

Python 3.12+, Django 5.2–6.1, django-mvp, Cotton, stripe 16 (`stripe-lite` extra), uv. Tests:
pytest with `tests/stripe_fake.py` for Stripe. No new dependency. No model and no migration.

## Constitution check

| Article | How the plan meets it |
|---|---|
| II Simplicity, III Anti-abstraction | One `Catalogue` class, one view, one template tag. No interface across backends, no override mechanism: per-placement replacement is composition |
| V Security | The checkout view requires sign-in, accepts only a price in the catalogue, validates `return_to`, and logs Stripe failures by error type only. Product text is rendered through the template layer |
| VI Documentation | Every public name is documented in the task that adds it |
| VIII i18n | Every visible string wrapped |
| X Cohesion | `Catalogue` groups read, filter, cache and clear. `Customer.start_checkout()` sits on the model beside `client_reference()` and `from_checkout()` |
| XI Interface and provider app | Stripe calls, the cache and the checkout live in `mvp_payments.stripe`. The interface reaches the catalogue through `apps.get_app_config()` and imports nothing from the app. Article XI's wording on where a plan is chosen is updated to say the plans are drawn here and paid for on Stripe's checkout |
| XII No script emitted | No provider script. The pricing table element is removed |
| XIII Installed, not wired | The plans page leaves the Account Center contribution and gets its own URLconf. Article XIII is amended: a project includes `mvp_payments.urls` once and, to offer the plans page, `mvp_payments.plans_urls` at the address it chooses |
| XV Money | Amounts through `Money`, tested with JPY and KWD |
| XVI Compatibility | Nothing has been released. Removals are recorded in the CHANGELOG, with no aliases |

## Design

### Stripe app (`mvp_payments/stripe/`)

- **`catalogue.py` — `Catalogue`** (classmethods): `prices() -> list[dict] | None` reads the
  cache key `mvp_payments_stripe:catalogue`; on a miss lists prices
  (`active=true`, `type=recurring`, `expand[]=data.product`, `limit=100`, every page), keeps
  those with an active product, `billing_scheme == "per_unit"`, a non-null `unit_amount` and
  `recurring.usage_type == "licensed"`, orders them (products by cheapest price, prices by billing
  length), stores the plain-dict list for `timeout()` seconds and returns it. A missing secret
  key or a Stripe error is logged by error type and returns `None`, caching nothing.
  `price(price_id) -> dict | None` returns the price on offer with that id. `clear()` deletes the
  key. `timeout()` reads `MVP_PAYMENTS["STRIPE_CATALOGUE_TIMEOUT"]`, default 3600.
- **`apps.py`** — `StripeConfig.catalogue`, a property returning `Catalogue` (imported inside it),
  which is how the interface reaches it.
- **`models.py`** — `Customer.start_checkout(user, price_id, success_url, cancel_url) -> str`
  creates the Checkout Session and returns its URL. Raises `stripe.StripeError`.
  `pricing_table_client_secret()` is removed. `client_reference()`'s docstring stops naming the
  pricing table.
- **`views.py`** — `CheckoutView(LoginRequiredMixin, View)`, POST only: safe `return_to` (else
  the plans page), price not in the catalogue → warning message and back, price held → the user
  subscriptions page, else `start_checkout` and redirect to Stripe; a Stripe error → error
  message and back. `BillingReturnView` reads `session_id` and, when the user has no customer,
  ties one with `Customer.from_checkout()` before syncing. `webhook` clears the catalogue on any
  verified `product.*` or `price.*` event and answers 200.
- **`urls.py`** — `stripe/checkout/`, name `stripe-checkout`.
- **`management/commands/stripe_sync.py`** — clears the catalogue before syncing.

### Interface (`mvp_payments/`)

- **`namespaces/stripe_plans.py` — `PlanChoices.for_request()`** kept from the sketch, reading
  `apps.get_app_config("mvp_payments_stripe").catalogue.prices()`, with the `?sketch=` handling
  removed. `namespaces/stripe_catalogue.py` is deleted.
- **`templatetags/mvp_payments.py`** — `stripe_plans`, `price_money`, `price_frequency`,
  `price_interval` kept, with real docstrings and no lazy imports.
- **`views.py` — `PlansPageView(MVPTemplateView)`** public, no sketch notices. The plans page
  `Page` stays out of the Stripe contribution. `SubscriptionPageView` reverses
  `payments_plans:stripe-plans`, `None` when the project has not mounted it.
- **`plans_urls.py`** — `app_name = "payments_plans"`, one route, `stripe-plans`, only when the
  Stripe app is installed.
- **Templates** — the approved components and page template kept. The sketch's inline notice is
  removed. Removed: `cotton/stripe/pricing_table.html`, `sign_in_notice.html`,
  `static/mvp_payments/stripe/pricing_table.js`.

### Demo

`/plans/` mounted, Plans in the sidebar, the landing section kept. File-based cache in a
git-ignored directory. Offline seed primes the cache with a demo catalogue (Basic, Pro, Team,
monthly and yearly). The pricing-table settings, pages and routes are removed.

### Documentation

`docs/reference/plans-page.md` rewritten (page, parts, data names, tag, settings, mounting,
placing and replacing, cache and webhook events). `docs/reference/stripe-app.md` (catalogue,
checkout view, settings). `docs/how-to/install-the-stripe-app.md` (the second include).
`docs/how-to/point-stripe-at-the-webhook.md` (product and price events). README, CHANGELOG,
CONTEXT.md, CONSTITUTION.md Articles XI and XIII, ADRs 0010 and 0012 brought to current state,
`specs/003-pricing-table/spec.md` rewritten to describe the plans page as it now is, and two new
ADRs: the plans are drawn from a cached catalogue and bought through a checkout the app starts,
and the plans page has an address of its own.

## Complexity tracking

| Addition | Why it is needed |
|---|---|
| A second URLconf for projects to include | Sam ruled the plans page public, outside the account address. An address outside the Account Center's include has to come from a second include, and the project chooses it |
| `STRIPE_CATALOGUE_TIMEOUT` setting | FR-015 asks for an expiry a project can change |
| Template tag | FR-019: plans in any template with no view of the project's own |

## Stories and order

Sequential, one implementer at a time: US2–US4 all touch the views, the plans page reference and
the tests US1 creates. US1 is dispatched alone, then US2–US4 together. Governance documents
(constitution, ADRs, CONTEXT, spec 003) are written at convergence.
