# django-mvp-payments

Pricing, checkout and subscription UI for [django-mvp](https://github.com/django-mvp/django-mvp)
projects, as Cotton components — one namespace per payment backend.

Django has no shortage of packages that talk to a payment provider. What none of them give you
is the part your users look at. A package hands you a subscription record, a list of prices and
an endpoint that starts a checkout, and leaves the plan grid, the subscribe button, the billing
panel and the "your card expires next month" notice to be built from raw utility classes — in
every project, every time.

This package is that layer and nothing else. It owns no data and runs no payment logic, and it
depends on no payment backend. What it does do is bring its own pages with it: install it
alongside a backend and the pages for that backend turn up in django-mvp's Account Center, rather
than leaving you to build and route them.

## Status

Version 0.0.1. The `drf-stripe` namespace contributes one entry to the Account Center,
Subscription, under a Billing group. That page is built: it shows a signed-in person what they are
currently subscribed to, what each plan grants them, the way to switch plans, and the way through
to the provider's billing portal. The plans page it leads to is routed and reachable but does not
show anything yet. Nothing here is stable.

## Requirements

- Python 3.12+
- Django 5.2 or 6.0
- django-mvp 0.23.0+
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
Stripe's own billing portal. It also carries the way to the plans page, which is routed and
reachable but does not show anything yet. Namespaces for other backends
are welcome and do not need this one's agreement about anything: adding one is adding it beside
the ones already installed, and changes nothing about their navigation entries, their card or
their pages.

[docs/subscription-page.md](docs/subscription-page.md) covers the subscription page: what it puts
in the template context, the components it is built from, and how to replace it with your own.

[docs/namespaces.md](docs/namespaces.md) is how you add a namespace: what one declares, the two
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

**What this is.** A presentation layer for payment and subscription state. Templates, the small
amount of JavaScript some components need, and just enough Python to put a page at a URL and an
entry in a menu.

Two ways of building a page are supported equally. A **native** component renders your backend's
own data as daisyUI markup, so it themes with the rest of your site and can show a person their
own state. A **provider embed** — Stripe's pricing table, for instance — is a thin wrapper around
the drop-in the provider already publishes, which is the faster answer where there is no
signed-in user to reflect. Neither is the fallback for the other.

The standing directions this package works toward are in [GOALS.md](GOALS.md).

**What this deliberately is not.**

- **Not a payment integration.** No API calls from Python, no webhook handling, no card data,
  no secrets, no money moving anywhere. Those are the backend's job and they are genuinely hard
  to get right; a UI package has no business having an opinion about them.
- **Not a way to run two backends at once.** Swapping one for another is a supported move and
  the reason namespaces do not share anything. Running two side by side is not: whose
  subscription a person is looking at stops being answerable, and nothing here is built to
  arbitrate it.
- **Not a backend abstraction.** There is no common interface that every payment library gets
  adapted onto. That abstraction is the classic trap in this domain: it fits the first library,
  bends for the second and is a liability by the third, because subscription models genuinely
  differ. A namespace per backend costs some duplication and buys the freedom to match each one
  exactly.
- **Not an owner of data.** No models, no migrations, no forms, no admin, no serializers. A page
  here has whatever view it needs, built on django-mvp's own view classes; every value on it was
  decided by the backend or by your project.
- **Not a CSS framework.** Components render the daisyUI classes django-mvp already ships. No
  stylesheet, no build step, no theme of its own.

**Tie-breaks.** When two of these pull against each other: match the backend rather than
generalise; route and render rather than compute; render less rather than assume how a page is
laid out.

## Licence

MIT.
