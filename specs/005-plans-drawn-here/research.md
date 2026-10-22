# Research — 005 Show the plans we offer and let only signed-in users buy one

Read against `origin/main` at `ee7895d` on 2026-10-22, after the sketch was approved.

## Planning notes, answered

### "Read the active prices and their products from Stripe and keep them in Django's cache, rather than copying them into models. The webhook endpoint already in the package clears the cache when a product or price changes (`product.*`, `price.*` events). The cache also expires on a timer, as a backstop for a missed webhook."

**Adopted.** `GET /v1/prices` takes `active=true`, `type=recurring` and `expand[]=data.product`,
so one paginated list call returns every price with its product. The Stripe app reads it with the
client it already builds (`mvp_payments/stripe/client.py`), walks every page with the SDK's
`auto_paging_iter()`, turns each price into plain dictionaries with `to_dict()`, and stores the
list under one key in Django's default cache. The webhook already verifies every event before
reading it. Product and price events are added as a branch that clears the key. The timeout is a
setting, `MVP_PAYMENTS["STRIPE_CATALOGUE_TIMEOUT"]`, in seconds, defaulting to 3600.

### "Start Stripe Checkout from a view of our own that requires sign-in, and create the session on the server with the user's existing Stripe customer and the signed checkout reference. That way Stripe never sees a purchase that isn't tied to an account. Checkout itself stays on Stripe's hosted page."

**Adopted.** A `CheckoutView` in the Stripe app, behind `LoginRequiredMixin`, accepts a POST
naming a price, refuses a price that is not in the catalogue, and creates a Checkout Session in
`subscription` mode with `client_reference_id` from `Customer.client_reference(user)`, the
user's existing `customer` or else `customer_email`, `allow_promotion_codes`, and success and
cancel addresses. It redirects to the session's `url`. The success address is the Stripe app's
existing return view with `?session_id={CHECKOUT_SESSION_ID}`, which Stripe fills in. The return
view passes it to the existing `Customer.from_checkout()`, so a first purchase is recorded before
the webhook arrives (FR-011).

### "Plans and prices are managed in Stripe's product catalogue. Product metadata or marketing features can carry a short description or feature list for each plan card."

**Adopted, without metadata.** Stripe's product already has `description` and
`marketing_features` (a list of `{name}`), edited in its dashboard. Using them needs no
convention of this package's.

### "Product and Price models are not needed for this. They would be worth adding only when a project needs reports or queries by plan, or a catalogue too large to fetch, and they would be kept in step through the same webhooks."

**Adopted.** No model is added. Recorded as the "revisit if" of the new ADR.

### "The plan cards are new design, so they should be sketched and agreed on the running page before they are built."

**Done.** Approved in round 2. The approved templates are kept as they are.

### "I assume we will be building the page from a json payload from Stripe?"

**Adopted.** The cached list is Stripe's JSON as plain dictionaries, and every component reads
Stripe's own field names.

### Alpine.js templating for customisation, replaced by Cotton parts

**Adopted as agreed: Cotton components, rendered on the server.** The outer `<c-stripe.plans>`
takes the whole set, and `<c-stripe.plan-card>`, `<c-stripe.plan-price>`,
`<c-stripe.plan-features>` and `<c-stripe.plan-choose>` each take one price or product. A project
replaces a part for the whole site by shipping a template at the same path. For one placement it
writes its own loop over `plans.prices` and composes the parts it keeps with its own markup for
the one it replaces, so no per-placement override mechanism is needed. Alpine only switches the
billing frequency.

## What the sketch needs, and how each is met

- **Every price on offer, product expanded** — the catalogue above, filtered to
  `billing_scheme == "per_unit"`, a non-null `unit_amount`, `recurring.usage_type == "licensed"`
  and an active product (FR-003). Stripe has no filter for these, so they are applied to the list.
- **Ordering** — products by their cheapest price, a product's prices by billing length, kept
  from the sketch's `PlanChoices`.
- **Billing frequencies, labels, starting frequency** — kept from the sketch's `PlanChoices`.
- **Prices the reader holds** — `Subscription.objects.for_user(user).current()`, already used by
  the user subscriptions page.
- **The picked price** — `?plan=` on the page's own address, from the sign-in link's `next`.
- **Addresses** — `settings.LOGIN_URL`, the checkout view, the user subscriptions page, the page
  path, all reversed or resolved at render.
- **Plans in any template** — the sketch's `{% stripe_plans as plans %}` tag is kept. The plans
  page view puts the same value in its context.
- **Notices on return** — Django's messages framework. `mvp/base.html` already renders
  `<c-mvp.messages>` in the shell above the page, so the checkout view adds a message and
  redirects, and no template carries a notice of its own.
- **Public address** — a second URLconf, `mvp_payments/plans_urls.py`, that a project includes
  where it wants the page. The interface's `mvp_payments.urls` stays the Account Center's.

## What the sketch faked, and how each is replaced

- **Catalogue** (`namespaces/stripe_catalogue.py`) — deleted. `PlanChoices` reads the Stripe app's
  catalogue through `apps.get_app_config("mvp_payments_stripe")`, so the interface still imports
  nothing from the provider app (Article XII, `tests/test_app.py`).
- **Checkout** (`CheckoutView` redirecting back) — the real view above.
- **Failure notices** (`?sketch=`) — messages added by the checkout view.
- **`price_demo_regular` reuse** — the demo's offline seed primes the cache with a demo catalogue
  whose Basic monthly price uses that id. Online, the sandbox's own catalogue is read.
- **Per-placement replacement** — composition, as above, documented with an example.
- **Pricing table still present** — removed: the component, `pricing_table.js`,
  `sign_in_notice.html`, `Customer.pricing_table_client_secret()`, the two settings, the demo's
  two pricing-table pages and their routes, and their tests.

## Unknowns settled

- **Login redirect.** `LoginRequiredMixin` sends an anonymous POST to the sign-in page and
  creates nothing, which meets FR-008 for any route. The plan card's own sign-in link carries
  `next=<page>?plan=<id>#<id>` (FR-010). allauth's sign-in honours `next` and its sign-up link
  carries it on.
- **Return-to safety.** The checkout view accepts the posted `return_to` only when
  `url_has_allowed_host_and_scheme` passes, and otherwise uses the plans page.
- **Absolute URLs for Stripe.** `request.build_absolute_uri()` on the reversed paths.
- **Demo cache.** The demo uses Django's file-based cache in a git-ignored directory, so the
  offline seed and the dev server share it.
- **Tests.** `tests/stripe_fake.py` already answers list endpoints and records requests, so
  "no second fetch" is an assertion on its request log. Tests run with the local-memory cache,
  cleared by an autouse fixture.

## What already exists

```
catalogue read and cache          · 7, new     · searched mvp_payments/stripe, stripe SDK has no cache; django.core.cache stores it
Stripe client                     · 2, repo    · mvp_payments/stripe/client.py client()
pagination over a list            · 3, package · stripe ListObject.auto_paging_iter()
JSON to plain dict                · 3, package · stripe StripeObject.to_dict()
cache storage and expiry          · 4, Django  · django.core.cache.cache
checkout session creation         · 3, package · client().v1.checkout.sessions.create
signed reference                  · 2, repo    · Customer.client_reference()
tie a completed checkout          · 2, repo    · Customer.from_checkout()
return from Stripe                · 2, repo    · BillingReturnView, extended with session_id
held prices                       · 2, repo    · SubscriptionQuerySet.for_user().current()
login redirect for the POST       · 4, Django  · LoginRequiredMixin
safe return address               · 4, Django  · django.utils.http.url_has_allowed_host_and_scheme
failure notices                   · 4, Django  · django.contrib.messages, rendered by mvp/base.html
amount formatting                 · 2, repo    · mvp_payments.money.Money, <c-stripe.amount>
frequency in words                · 2, repo    · CurrentSubscription.frequency_display
card, grid, button, badge, join   · 3, package · django-mvp <c-mvp.card>, <c-mvp.grid>; daisy-cotton <c-button>, <c-badge>, <c-join>
empty states                      · 3, package · <c-mvp.page.list.empty>
frequency switch                  · 5, browser · native radio inputs, Alpine x-model (bundled by django-mvp)
public page view                  · 3, package · mvp.views.MVPTemplateView, page_view.html
plans in any template             · 7, new     · template tag {% stripe_plans %}; searched mvp_payments/templatetags
```
