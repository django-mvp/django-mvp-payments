# Research — 002 Show a person the subscription they are on

What was read in the dependencies before planning, and what each reading settles. Everything here
is a fact about a version that is pinned in `poetry.lock`; nothing is an assumption about a
backend's future.

## What the backend records (drf-stripe-subscription 1.2.2)

`drf_stripe.models` holds six models. None of them is this package's, and this package imports
none of them — they are reached through `django.apps.apps.get_model`, which is the only route
Article XIII leaves open.

| Model | The fields this page reads |
|---|---|
| `StripeUser` | `user` (one-to-one with the project's user model, and the primary key), `customer_id` |
| `Subscription` | `subscription_id`, `stripe_user`, `status`, `period_start`, `period_end` |
| `SubscriptionItem` | `sub_item_id`, `subscription`, `price`, `quantity` |
| `Price` | `price_id`, `product`, `nickname`, `price` (an integer, in the currency's minor unit), `freq`, `currency` |
| `Product` | `product_id`, `name`, `description` |
| `Feature` / `ProductFeature` | `feature_id`, `description`; `ProductFeature` joins a product to a feature |

Three readings matter to the design.

**`StripeUser.current_subscription_items` is the backend's own definition of current.** It returns
the `SubscriptionItem` rows whose subscription's status is in the backend's
`ACCESS_GRANTING_STATUSES` — active, trialing, past due — which is the same filter the backend
applies when anything else asks what a person may reach. Reading that property and grouping its
rows by `item.subscription` yields the current subscriptions without this package naming a single
status, which is what FR-001 asks for. The alternative, filtering `Subscription` on a status list,
would mean copying the backend's list into this package, where it would silently go stale the day
the backend changed it.

**An amount arrives without a rendering.** `Price.price` is a `PositiveIntegerField` holding
Stripe's `unit_amount`, which is in the currency's minor unit, and `Price.currency` is the
three-letter code beside it. Nothing in the backend converts or formats. Article XVI requires the
conversion to be made explicitly against the currency, which is what `mvp_payments/money.py` is
for.

**A billing frequency is a composed string, not an interval.** `get_freq_from_stripe_price` writes
`f"{interval}_{interval_count}"`, so the stored values are `month_1`, `year_1`, `week_2` and so on,
and a price with no recurring component stores `None`. The page therefore has to read that shape,
and — like a status it does not recognise — show an unfamiliar one as itself rather than dropping
it.

**A feature's description defaults to its identifier.** `create_update_product_features` creates a
missing `Feature` with `description=feature_id`, so in practice the two are often equal. The
description can still be null for a row the project created itself, which is the case US-3's fourth
scenario is about.

## The portal endpoint

`drf_stripe.urls` mounts `customer-portal/` on `StripeCustomerPortal`, which is a DRF `APIView`
with `IsAuthenticated`. It answers a **POST** — not a GET — with `{"url": "..."}`, having asked
Stripe for a billing-portal session for the signed-in person's customer record. The route carries
no `name`, so it cannot be reversed; the only way for this page to know where it is mounted is to
be told, which is what FR-006 already says.

Two consequences for the design:

- The way through to the portal cannot be a plain link. It is a control that posts to the endpoint
  and follows the address that comes back, which is a few lines of JavaScript shipped as a static
  file (Article XIII), with the endpoint and the CSRF token rendered into the markup as data.
- The endpoint does **not** fail for a person the backend holds no customer record for. It calls
  `get_or_create_stripe_user`, which creates the row and, when it has no customer id, creates a
  brand-new customer at Stripe before minting a portal session for it
  (`drf_stripe/stripe_api/customers.py:188-192`). So the control has to be kept off the page for
  someone with nothing current, as FR-008 requires, or a person who never subscribed would create a
  customer record at the provider by clicking it. US-2's third scenario covers a failure reaching
  the endpoint for everyone else.

Session authentication is DRF's default and is what a signed-in browser already has, so the POST
needs the CSRF token and nothing else.

## What django-mvp already supplies

Read from django-mvp 0.23.0's `templates/cotton/`. The page is assembled from components that
already exist rather than new markup:

- `<c-card>` — a titled surface with `badges`, `actions` and `footer` slots. One current
  subscription renders as one card.
- `<c-badge>` — the status, with a variant from the daisyUI semantic palette.
- `<c-data_field>` — a labelled value, which is what the period and the frequency are.
- `<c-page.list.empty>` — an icon, a heading and a message. This is the no-subscription state, and
  it is why US-4 needs no markup of its own beyond a component that delegates to it.
- `<c-button>`, `<c-link>` — the control that leads to the provider.

`<c-page>` and `<c-page.title>` are already on the page from the previous feature.

## Formatting an amount without a new dependency

Django's `django.utils.formats.number_format` formats a `Decimal` with a fixed number of decimal
places under the active locale, which gives the grouping and the decimal separator a reader
expects. It does not know currencies.

The minor-unit exponent is therefore this package's to hold. Stripe's zero-decimal set is
documented and small (`BIF CLP DJF GNF JPY KMF KRW MGA PYG RWF UGX VND VUV XAF XOF XPF`), and
three-decimal currencies (`BHD IQD JOD KWD LYD OMR TND`) round to a unit of ten in Stripe's API.
Holding the two exceptional sets and defaulting the rest to two decimal places is a table of
twenty-three codes and is exact for every currency Stripe supports.

`babel` would supply both the exponent and a localised currency pattern. It was rejected: it is a
runtime dependency with a data bundle of its own, added for one table this package can state in a
dozen lines, against Article VII and Article II. The cost is that the currency is rendered as its
code beside the number rather than as a symbol in the locale's own pattern, which is accurate,
unambiguous and the thing an invoice does anyway.

## Where the package's existing shape already answers a requirement

- **Signing in** (FR-010) is `LoginRequiredMixin` on `PaymentPageView`, which the subscription
  page's view inherits. Nothing new.
- **Only the reader's own records** (FR-010) follows from reading them through the signed-in
  person's `StripeUser` rather than through a filter this page builds.
- **Overriding the template** (FR-011) is Django's app-directories loader, already how the demo
  supplies `base.html`. The requirement is not a mechanism to build but a context to name and
  document.
