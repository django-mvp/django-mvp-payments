# django-mvp-payments

[![Tests](https://github.com/django-mvp/django-mvp-payments/actions/workflows/tests.yml/badge.svg)](https://github.com/django-mvp/django-mvp-payments/actions/workflows/tests.yml)
[![Build](https://github.com/django-mvp/django-mvp-payments/actions/workflows/build.yml/badge.svg)](https://github.com/django-mvp/django-mvp-payments/actions/workflows/build.yml)
[![Publish](https://github.com/django-mvp/django-mvp-payments/actions/workflows/publish.yml/badge.svg)](https://github.com/django-mvp/django-mvp-payments/actions/workflows/publish.yml)
[![Coverage](https://codecov.io/gh/django-mvp/django-mvp-payments/branch/main/graph/badge.svg)](https://codecov.io/gh/django-mvp/django-mvp-payments)
[![PyPI](https://img.shields.io/pypi/v/django-mvp-payments)](https://pypi.org/project/django-mvp-payments/)
[![Development status](https://img.shields.io/pypi/status/django-mvp-payments)](https://pypi.org/project/django-mvp-payments/)
[![Python](https://img.shields.io/pypi/pyversions/django-mvp-payments)](https://pypi.org/project/django-mvp-payments/)
[![Django](https://img.shields.io/pypi/djversions/django-mvp-payments)](https://pypi.org/project/django-mvp-payments/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Licence](https://img.shields.io/github/license/django-mvp/django-mvp-payments)](https://github.com/django-mvp/django-mvp-payments/blob/main/LICENSE)

Payment and subscription UI as Cotton components for django-mvp projects, one namespace per payment backend.

It covers pricing, checkout and subscriptions for
[django-mvp](https://github.com/django-mvp/django-mvp) projects.

Django has no shortage of packages that talk to a payment provider. What none of them give you
is the part your users look at. A package hands you a subscription record, a list of prices and
an endpoint that starts a checkout, and leaves the plan grid, the subscribe button, the billing
panel and the "your card expires next month" notice to be built from raw utility classes — in
every project, every time.

This package is that layer, plus the least it takes to keep it fed. It runs no payment logic and
depends on no third-party payment backend. For Stripe it is moving to an app of its own,
`mvp_payments.stripe`, which keeps a small copy of each user's subscription in step with Stripe
through webhooks. Either way it brings its own pages with it: they turn up in django-mvp's Account
Center, rather than leaving you to build and route them.

## Status

Version 0.0.1. The `drf-stripe` namespace contributes one entry to the Account Center,
Subscription, under a Billing group. That page shows a signed-in person what they are currently
subscribed to, what each plan grants them, the way to switch plans, and the way through to the
provider's billing portal. The plans page it leads to mounts the provider's own pricing table,
configured by two settings, and says so plainly when it has not been configured or when the
provider's library never arrived. Nothing here is stable.

## Requirements

- Python 3.12+
- Django 5.2, 6.0 or 6.1
- django-mvp 0.30.0+
- A payment backend of your choosing, installed and configured separately

## Install

```bash
pip install django-mvp-payments
```

Add it to `INSTALLED_APPS`, before `mvp`:

```python
INSTALLED_APPS = [
    ...,
    "mvp_payments",
    "mvp",
]
```

That order is load-bearing, not a style choice: this package ships its own copy of
`mvp/account/overview.html` and extends the name from inside it, which only resolves when this
application is found first.

Then mount its URLs wherever you like:

```python
urlpatterns = [
    ...,
    path("account/billing/", include("mvp_payments.urls")),
]
```

Mount it where a reader would expect to find it. These are Account Center pages, so inside the
Account Center's own prefix and under the label the navigation gives them is the natural place.
Addresses carry no backend name: a page is at `<your prefix>/subscription/`, never
`<your prefix>/some-library-name/subscription/`, because which library you chose to talk to your
payment provider is not a person's business while they read their own subscription.

That line is the only wiring. From there, every backend you have installed contributes its own
section of the Account Center's navigation and its own card to the Account Center's overview, and a
backend you have not installed contributes nothing. There is no settings block, no flag to turn on
and no registry to populate — what is in `INSTALLED_APPS` decides what exists.

### The Stripe app

To keep each user's Stripe subscription in your database, install the extra and add the app:

```bash
pip install "django-mvp-payments[stripe-lite]"
```

```python
INSTALLED_APPS = [
    ...,
    "mvp_payments",
    "mvp_payments.stripe",
    "mvp",
]
```

Then set `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` in `MVP_PAYMENTS` and run
`python manage.py migrate`.
[docs/stripe.md](https://github.com/django-mvp/django-mvp-payments/blob/main/docs/stripe.md)
has the steps, the settings and the records.

## Namespaces

Components are grouped by the backend they speak to, and the namespace is that backend's name:

```html
<c-drf-stripe.plan-grid />
<c-drf-stripe.subscribe-button price-id="price_123" />
```

Each namespace assumes one backend's HTTP endpoints and nothing else. Two namespaces never
share markup or a data shape, because the things they are describing are not the same thing
wearing different names — a subscription in one library is a different record with different
fields from a subscription in the next.

Shipped today: `drf-stripe`, built against
[drf-stripe-subscription](https://github.com/oscarychen/drf-stripe-subscription), which handles
webhooks locally and hands checkout and billing management to Stripe's hosted pages. It
contributes a subscription page and a plans page, of which only the first is in the navigation.
The subscription page shows what a person is currently subscribed to, reading the backend's own
records directly and calling one of its HTTP endpoints, `customer-portal/`, to hand the reader to
Stripe's own billing portal. It also carries the way to the plans page, which mounts the
provider's own pricing table from two settings. Namespaces for other backends
are welcome and do not need this one's agreement about anything: adding one is adding it beside
the ones already installed, and changes nothing about their navigation entries, their card or
their pages.

[docs/subscription-page.md](https://github.com/django-mvp/django-mvp-payments/blob/main/docs/subscription-page.md) covers the subscription page: what it puts
in the template context, the components it is built from, and how to replace it with your own.

[docs/plans-page.md](https://github.com/django-mvp/django-mvp-payments/blob/main/docs/plans-page.md) covers the plans page: the component it mounts, the
settings it reads, and how to replace the component or the page with your own.

[docs/namespaces.md](https://github.com/django-mvp/django-mvp-payments/blob/main/docs/namespaces.md) is how you add a namespace: what one declares, the two
questions it answers about itself, and what it may not do.

## JavaScript

A component that starts a checkout needs the provider's own script, and Stripe in particular
forbids self-hosting `stripe.js`. This package does not emit a script tag for it.

Loading the libraries your components need is your project's decision — a CDN tag, a bundler
entry point, an import map, whatever you already use. Where a component needs logic of its own
beyond that, it arrives as a small static file you include the same way. The demo project loads
Stripe from their CDN, which is the right trade for looking at something locally and the wrong
one to copy into production without thinking about it.

## Scope & philosophy

**What this is.** A presentation layer for payment and subscription state, and, for each
supported provider, a small app that keeps that state. Templates, the small amount of JavaScript
some components need, the Python that puts a page at a URL and an entry in a menu, and for
Stripe, `mvp_payments.stripe`.

The pages look like the rest of your django-mvp site, because they are drawn with the same daisyUI
classes and follow the same theme. They show a person where they stand. Anything that changes
what they pay, such as choosing a plan, switching, cancelling or updating a card, is handed to the
provider's own hosted pages, which already do it well. Where the provider publishes a drop-in,
such as Stripe's pricing table, a page mounts it rather than rebuilding it.

The Stripe app keeps the least it can: who each user's Stripe customer is, and that customer's
subscription with its status, price and period. Stripe is the source of truth. The app learns of
changes from Stripe's webhooks, checks each one's signature and then asks Stripe for the current
state, rather than trusting what the webhook says. It is installed with
`django-mvp-payments[stripe-lite]`. Today's pages still read drf-stripe-subscription's records
until they move to it ([ADR 0010](https://github.com/django-mvp/django-mvp-payments/blob/main/docs/adr/0010-the-package-ships-its-own-stripe-app.md)).

The standing directions this package works toward are in [GOALS.md](https://github.com/django-mvp/django-mvp-payments/blob/main/GOALS.md).

**What this deliberately is not.**

- **Not a full Stripe integration.** No copy of Stripe's products, prices, invoices or payment
  methods, no taxes, no metered billing, no one-off payments. If you need those,
  [dj-stripe](https://github.com/dj-stripe/dj-stripe) is built for it.
- **Not a decider.** Nothing here computes a price, a proration or a trial, and nothing decides
  what a subscription grants. The Stripe app can tell your views whether someone is subscribed.
  What that lets them see is your project's call, enforced in your views.
- **Not a place card details pass through.** Cards are typed into the provider's own pages and
  iframes, never into markup written here.
- **Not a way to run two backends at once.** Whose subscription a person is looking at stops
  being answerable, and nothing here is built to arbitrate it.
- **Not a backend abstraction.** There is no common interface that every payment provider gets
  adapted onto. That abstraction is the classic trap in this domain: it fits the first provider,
  bends for the second and is a liability by the third, because subscription models genuinely
  differ. A namespace per backend costs some duplication and buys the freedom to match each one
  exactly.
- **Not a CSS framework.** Components render the daisyUI classes django-mvp already ships. No
  stylesheet, no build step, no theme of its own.

**Tie-breaks.** When two of these pull against each other:

- match the provider rather than generalise
- keep less rather than more, and ask the provider rather than guess
- route and render rather than compute
- render less rather than assume how a page is laid out

## Running the demo

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver 8020
```

Sign in as `regular.user`, `staff.user` or `super.user`, password `password`. Out of the box the
pages run on fake Stripe values, so the billing portal and the pricing table say they could not be
reached. To see them working, copy `demo/.env.example` to `demo/.env` and fill it in from your own
Stripe sandbox. That file is gitignored. Then run `seed_demo` again so the demo accounts get real
sandbox customers and subscriptions. The file lists the one portal setting "Switch plans" needs
from your sandbox.

## Contributing

Changes follow [CONSTITUTION.md](https://github.com/django-mvp/django-mvp-payments/blob/main/CONSTITUTION.md), the
[testing standards](https://github.com/django-mvp/django-mvp-payments/blob/main/docs/contributing/standards/testing.md), the
[code documentation standards](https://github.com/django-mvp/django-mvp-payments/blob/main/docs/contributing/standards/code-documentation.md) and the
[Django standards](https://github.com/django-mvp/django-mvp-payments/blob/main/docs/contributing/standards/django.md).

## Changelog

See [CHANGELOG.md](https://github.com/django-mvp/django-mvp-payments/blob/main/CHANGELOG.md).

## Licence

MIT.
