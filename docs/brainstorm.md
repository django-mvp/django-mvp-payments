# Working notes

Conclusions from the conversation that started this package. These are notes, not decisions on
the record — an accepted decision belongs in `docs/adr/` and none of these has been through
that.

## Prior art

Django has plenty of payment packages, and none of them does what this one does.

| Package | State, September 2026 | What it is |
|---|---|---|
| [dj-stripe](https://github.com/dj-stripe/dj-stripe) | 2.11.0, active, ~1.8k stars | Mirrors Stripe's data model into your database |
| [django-payments](https://github.com/jazzband/django-payments) | 4.1.0, active, ~1.2k stars | Multi-provider payment handling, jazzband-maintained |
| [drf-stripe-subscription](https://github.com/oscarychen/drf-stripe-subscription) | 1.2.2 (Nov 2024), single maintainer, ~120 stars | Webhook handling plus REST endpoints, checkout via Stripe's hosted pages |

All three are backend packages. None ships UI: dj-stripe and django-payments give you models and
plumbing, drf-stripe-subscription gives you six JSON endpoints and assumes a JavaScript frontend
is rendering them. The pricing page and the billing panel are left to the adopter in every case,
which is the gap this package fills. There is no overlap to defend.

## Why drf-stripe-subscription is the first namespace

dj-stripe is the obvious default and was rejected deliberately. The common complaint about it is
that it is *too* complete: it replicates Stripe's data model inside your application, which is a
large surface to carry, keep in sync and reason about. A frequent recommendation among people who
have run payments in production is the opposite — handle the webhooks you care about, keep your
own business logic small and specific, and let Stripe host the parts that touch card data.

drf-stripe-subscription sits at that balance. Webhooks are handled for you, local state stays
narrow, and checkout and billing management are Stripe's hosted pages rather than application
logic.

### The constraint that comes with it

drf-stripe-subscription pins `pydantic>=1.8,<2.0` and imports `stripe.error.StripeError`, which
was removed in stripe-python v8 (September 2023). Pydantic 1.x is end of life. Its test matrix
tops out at Django 5.0 and Python 3.12. A project adopting it therefore holds pydantic at 1.x and
`stripe` below 8, which is a real constraint on that project and worth knowing before committing
to it.

This package is unaffected, and that is the point of the design rather than a happy accident. It
declares no dependency on any backend, so none of those pins reach a project that installs it,
and none of them reach this repository's own test environment either. If the backend has to be
replaced, the UI layer outlives it.

## Why a namespace per backend, and no common interface

The tempting design is an adapter layer: one set of components, a defined interface, a shim per
payment library. It was rejected.

Subscription models genuinely differ between these libraries — what a price is, whether features
are modelled at all, how a trial and a cancellation are represented, what a "subscription item"
means. An interface that spans them fits the first library it was drawn from, bends for the
second and constrains the third. The cost of avoiding it is some duplicated markup between
namespaces. That is cheaper than the abstraction, and it means a namespace can match its backend
exactly instead of matching the interface.

Should real commonality prove itself once a second namespace exists, it can be extracted then,
from evidence rather than from anticipation.

## Why no Python

The package could ship thin server-rendered views so that markup gets its data from the template
context. It deliberately does not.

Adding views means URLs to mount, permissions to decide and a request cycle to own, and it makes
the package a participant in the application rather than a supplier of markup. drf-stripe-
subscription already exposes the data over HTTP and expects the browser to call it, so the
components follow that grain. Nothing in the package imports Django beyond an `AppConfig`.
