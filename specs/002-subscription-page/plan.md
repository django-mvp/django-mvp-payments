# Implementation Plan: Show a person the subscription they are on

**Branch**: `002-subscription-page` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-subscription-page/spec.md`

## Summary

The drf-stripe namespace's subscription page gets a view of its own. It asks the signed-in person's
`StripeUser` for the subscription items the backend itself calls current, groups them by their
subscription, and turns each into a small presentation object carrying a status, a period and its
priced items. Every value on it is one the backend recorded; the only transformation is rendering
an amount in its currency's own unit, which Article XVI requires and which is done against a table
of currency exponents rather than by assuming two decimal places.

The page is assembled from Cotton components in the `drf_stripe` namespace, each rendering from its
own attributes, so a project can place one in a template of its own or replace the page's template
entirely and still have every value under a documented name. The way through to the provider's
portal is a control that posts to the backend's own endpoint — whose location the project supplies,
because the project is what mounts it — and follows the address that comes back.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.14)

**Primary Dependencies**: Django 5.2 and 6.0, django-mvp 0.23.0. No payment backend, now or ever —
`tests/test_app.py` asserts the runtime dependency set is exactly `{django, django-mvp}`, and this
feature adds nothing to it.

**Storage**: none. The package defines no model and ships no migration. Every record this feature
reads belongs to the installed backend and is reached through `apps.get_model`.

**Testing**: pytest with pytest-django, settings inherited from `demo/settings.py` by
`tests/settings.py`. Factories for the backend's models live in `tests/factories.py` — a factory for
a model this package does not own, which is the only way to put a subscription in front of the
page. Assertions are made against rendered output (Article XVI).

**Target Platform**: a Django project that has installed django-mvp and drf-stripe-subscription and
mounted both their URL configurations.

**Project Type**: installable Django application — templates, a small amount of routing and reading
Python, one static file, no data.

**Constraints**: no import of the backend anywhere in `mvp_payments/` (Article XIII); no figure
computed from more than one recorded value (FR-007, Article XII); nothing at import time touches the
application registry, reverses a URL or reads settings (Article XIV).

**Scale/Scope**: one page, six components, one reader module, one formatting module, one static
file, five user stories.

## Constitution Check

Read before planning, re-checked against the design below.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Test-First | Every behaviour is observable in a rendered page or a component's output, so each task has a failing test before it has code | Pass |
| II Simplicity / III Anti-Abstraction | Two new modules, each with one concrete job and one caller. No base class, no registry, no second implementation anticipated | Pass |
| IV Integration-First | The page is exercised through the test client as a reader reaches it, and each component is rendered standalone | Pass |
| V Security | Every value reaches the page through the template layer. The portal endpoint's address is configuration, not a secret, and no key of any kind is read | Pass |
| VI Documentation | `docs/subscription-page.md` is new and linked from the README; CHANGELOG entry; docstrings on every public surface | Pass |
| VII Dependency discipline | No dependency added, runtime or development. `babel` considered and rejected in `research.md` | Pass |
| VIII Internationalization | Every label, status word, empty-state sentence and control caption is wrapped; the frequency's plural forms go through `ngettext` | Pass |
| IX Data-model conventions | No model, no field, no migration | Not applicable |
| X Test structure | Every new test module mirrors its source module; component tests go under the already-declared `non-mirror-paths` entry | Pass |
| XI Cohesion | The reading of the backend's records is grouped on one class per presentation object, and the amount formatting on one frozen dataclass. No module of loose functions | Pass |
| XII Interface layer | The page reads records and renders them. It computes no charge, reaches no provider, and adds no model, form, admin or serializer. The one sum it could have shown — a total across items — is refused by FR-007 and by this article for the same reason | Pass |
| XIII No backend dependency | `apps.get_model` throughout; no `import drf_stripe` anywhere in the package. `tests/test_app.py`'s existing assertion covers it | Pass |
| XIV Installation, not configuration | Unchanged: the page appears because the backend is installed. The portal endpoint's location is configuration the page *reads*, not a gate on whether the page exists — without it the page still renders and says the portal cannot be reached | Pass |
| XV One namespace per backend | Everything that knows what a subscription is lives under `namespaces/drf_stripe*`. `money.py` is the plumbing Article XV names as shared — formatting an amount for display | Pass |
| XVI Rendered output is a contract | The whole feature. An amount is converted against its currency and tested with a zero-decimal and a three-decimal currency; an unrecognised status and an unrecognised frequency render as themselves; the status is a badge with text, never colour alone; the portal control announces that it leads off-site | Pass |
| XVII Compatibility | New components and a new context are additive; both are listed in the CHANGELOG, and the namespace's documented endpoint list gains `customer-portal/` | Pass |

## Project Structure

### Documentation (this feature)

```text
specs/002-subscription-page/
├── spec.md              # merged to main at the spec gate
├── decisions.md         # merged with it; appended to here
├── plan.md              # this file
├── research.md          # what was read in the dependencies
├── tasks.md             # the task graph
├── progress.md          # run narrative
└── feature-state.json   # the ledger
```

No `data-model.md`: the feature defines no data. No `contracts/`: the rendered page is the
contract, and Article XVI already says how it is asserted.

### Source code

```text
mvp_payments/
├── contributions.py                     # Page gains `view`; url_patterns() builds from it
├── views.py                             # SubscriptionPageView beside PaymentPageView
├── money.py                             # new — Money: minor units + currency → a rendered amount
├── namespaces/
│   ├── drf_stripe.py                    # the contribution declares the new view for its page
│   └── drf_stripe_records.py            # new — the backend's records as presentation objects
├── static/mvp_payments/drf_stripe/
│   └── billing_portal.js                # new — posts to the endpoint, follows the address back
└── templates/
    ├── mvp_payments/drf_stripe/
    │   └── subscription.html            # the page, assembled from the components below
    └── cotton/drf_stripe/
        ├── subscription.html            # one current subscription
        ├── plan.html                    # one priced item: name, amount, frequency, features
        ├── amount.html                  # a rendered amount with its currency
        ├── features.html                # a plan's features
        ├── portal_link.html             # the control that leads to the provider
        └── no_subscription.html         # the empty state

tests/
├── factories.py                         # new — one factory per backend model the page reads
├── conftest.py                          # fixtures over those factories
├── test_money.py                        # new
├── test_views.py                        # extended: the page's context and its rendering
├── test_contributions.py                # extended: a Page's view
├── test_namespaces/
│   └── test_drf_stripe_records.py       # new
└── test_components/                     # new — one module per component, declared non-mirroring
    └── test_drf_stripe.py

demo/
└── management/commands/seed_demo.py     # extended: subscriptions for the accounts to look at

docs/
└── subscription-page.md                 # new — the context names and the components
```

**Structure Decision**: the namespace stays a module rather than becoming a package. A second
module beside it, `drf_stripe_records.py`, holds the reading; splitting it out keeps the
contribution declaration a declaration and avoids the import cycle that putting a view's dependency
inside the contribution module would create. `money.py` sits at the package root because Article XV
names amount formatting as plumbing every namespace would otherwise duplicate.

## Design

### Reading the backend's records

`namespaces/drf_stripe_records.py` holds three frozen dataclasses and one reader:

- `CurrentSubscription` — `status`, `period_start`, `period_end`, `plans`.
- `Plan` — `name`, `amount` (a `Money`), `frequency`, `quantity`, `features`.
- `PlanFeature` — `identifier`, `description`.
- `SubscriptionReader` — `for_user(user)` returns the current subscriptions, newest first.

`for_user` resolves `StripeUser` through `apps.get_model("drf_stripe", "StripeUser")`, returns an
empty tuple when the person has no customer record at all, and otherwise reads
`current_subscription_items` — the backend's own definition of current (FR-001) — with
`select_related` down to the product and `prefetch_related` on the product's features, groups the
rows by `item.subscription`, and builds the dataclasses. A plan's name is `price.nickname` where it
is set and `product.name` otherwise (FR-003). A feature's display text is its description where the
project set one and its identifier otherwise (FR-009).

No status is named anywhere in this module, and no amount is added to another.

### Rendering an amount

`money.py` holds `Money`, a frozen dataclass of `minor_units` and `currency`, with:

- `EXPONENTS` — the zero-decimal and three-decimal currency sets from `research.md`; everything
  else is two.
- `amount` — the `Decimal` in the currency's own unit, scaled by that exponent.
- `__str__` — `number_format` under the active locale, followed by the currency code.

A `Money` with no currency renders nothing (Article XVI). The class holds one amount and never
combines two.

### The page and its context

`Page` gains a `view` field defaulting to `PaymentPageView`, and `url_patterns()` builds each route
from `page.view`. The drf-stripe contribution names `SubscriptionPageView` for its subscription
page and leaves the other two unchanged.

`SubscriptionPageView` adds two names to the context, and these are the documented surface FR-011
promises:

| Name | What it is |
|---|---|
| `subscriptions` | the reader's current subscriptions, each with `status`, `period_start`, `period_end` and `plans` |
| `billing_portal_endpoint` | where to post for a portal address, or `None` |

`billing_portal_endpoint` is read from `settings.MVP_PAYMENTS["DRF_STRIPE_BILLING_PORTAL"]`, absent
by default, and is `None` for a person with no current subscription whatever the setting says
(FR-008).

### The way through to the provider

`portal_link.html` renders a button carrying the endpoint and a CSRF token as data, an
`aria-describedby` note that it leads to the provider's site, and an empty, `hidden` element for the
failure message. `billing_portal.js` binds to the button, posts, follows the `url` in the answer,
and on any failure reveals the message instead (US-2 scenario 3). The project loads the file the way
it already loads its own static assets; the demo loads it, and the README's JavaScript section
already sets that expectation.

### Components

Each component takes its values as attributes and reads no context of its own, so it renders in an
unrelated template given its attributes (FR-012, SC-006). `subscription.html` takes one
`CurrentSubscription`; `plan.html` takes one `Plan`; `amount.html` takes a `Money`; `features.html`
takes a plan's features; `no_subscription.html` takes nothing. The page's own template is then a
loop over `subscriptions` with `no_subscription` as its `{% empty %}`.

An unrecognised status renders as itself with a neutral badge; the recognised ones get a variant
from django-mvp's palette, never colour alone (Article XVI). A frequency of `month_1` renders as a
translated interval through `ngettext`, and anything the table does not hold renders as itself.

## Phases

**Foundational** (sequential, before any story): `tests/factories.py` with one factory per backend
model the page reads, the fixtures in `conftest.py` that wrap them, and the demo's seed command
extended to create a subscription for `regular.user` so the page has something on it. Nothing in
`mvp_payments/` changes in this phase.

Then the stories in priority order, one at a time into a single worktree:

- **US-1** — `money.py`, `drf_stripe_records.py`, `Page.view`, `SubscriptionPageView`, and the
  `subscription`, `plan`, `amount` components. The page names the plan, the amount, the frequency,
  the status and the period.
- **US-2** — the endpoint setting, `portal_link.html`, `billing_portal.js`, and the statement that
  the provider manages the subscription.
- **US-3** — `features.html` and the feature reading behind it.
- **US-4** — `no_subscription.html` and the guarantee that nothing else appears with it.
- **US-5** — `docs/subscription-page.md`, the README link, the CHANGELOG entry, and the tests that
  hold the context names and the standalone rendering of every component.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| A currency-exponent table inside this package | Article XVI forbids assuming two decimal places, and the backend records only minor units and a code | `babel` is a runtime dependency with a data bundle, added for nineteen strings (Article VII) |
| A static JavaScript file | The backend's portal endpoint answers a POST and returns an address, so a plain link cannot reach it | A server-side redirect view would mean this package calling the backend's endpoint on a reader's behalf, which is a server-side call it does not get to make |
| `Page` gains a `view` field | One page in one namespace now needs context the generic page view cannot supply | A separate URL configuration for the subscription page would put the same page's route in two places and break the rule that a contribution declares everything it contributes |
