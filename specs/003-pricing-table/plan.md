# Implementation Plan: Offer plans through the provider's own pricing table

**Branch**: `feat/003-pricing-table` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-pricing-table/spec.md`

## Summary

One Cotton component in the `drf_stripe` namespace emits the provider's `<stripe-pricing-table>`
element and its attributes, and nothing else. It takes the pricing table identifier, the
publishable key and an email address as attributes, so a project can place it in any template of
its own, for a reader who is not signed in.

The Plans page the namespace already contributes gets a view that reads the identifier and the key
from `settings.MVP_PAYMENTS` and hands them to that component — the same thing the subscription
page already does for the backend's portal endpoint. Where either is missing, the page says the
plans cannot be shown and emits no element at all. Where the project did not load the provider's
library, a small static file reveals a message the component rendered hidden, because an undefined
custom element is an empty box with nothing in the page to explain it.

Nothing is computed. No amount, currency or billing frequency is produced anywhere in this feature
— every price a reader sees is rendered inside the provider's own frame.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.14)

**Primary Dependencies**: Django 5.2 and 6.0, django-mvp 0.23.0. No payment backend, now or ever —
`tests/test_app.py` asserts the runtime dependency set is exactly `{django, django-mvp}`, and this
feature adds nothing to it.

**Storage**: none. No model, no migration, no record read or written. This feature reads two
settings and one attribute of the request's user.

**Testing**: pytest with pytest-django, settings inherited from `demo/settings.py` by
`tests/settings.py`. Assertions are made against rendered output (Article XVI): the element, its
attributes, the absence of a script element, and the unavailable state's sentence.

**Target Platform**: a Django project that has installed django-mvp and drf-stripe-subscription,
mounted both their URL configurations, created a pricing table in the provider's dashboard and
loaded the provider's library however it manages its frontend.

**Project Type**: installable Django application — one component, one view, one static file, two
settings and documentation.

**Constraints**: no `<script>` element pointing at the provider anywhere in this package's output
(Article XIII, FR-002, SC-002); no figure about price (Article XII, FR-011, SC-007); the component
reads no settings (FR-003); nothing at import time reads settings (Article XIV).

**Scale/Scope**: one component, one view, one static file, one documentation page, five user
stories, one constitution amendment.

## Constitution Check

Read before planning, re-checked against the design below.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Test-First | Every behaviour is an assertion about rendered markup, so each task has a failing test before it has code | Pass |
| II Simplicity / III Anti-Abstraction | One component, one view subclass, one four-line static file. No abstraction over "embeds" — a second provider gets its own namespace (Article XV) | Pass |
| IV Integration-First | The page is exercised through the test client as a reader reaches it; the component is rendered standalone in a template of its own | Pass |
| V Security | Both values reach the markup through the template layer. Neither is a secret: a publishable key identifies an account and the provider prints it in its own examples. No key that could move money is read, held or emitted | Pass |
| VI Documentation | `docs/plans-page.md` is new and linked from the README; CHANGELOG entry; docstrings on the new view | Pass |
| VII Dependency discipline | No dependency added, runtime or development | Pass |
| VIII Internationalization | The unavailable sentence, the could-not-be-loaded sentence and the page's heading are wrapped | Pass |
| IX Data-model conventions | No model, no field, no migration | Not applicable |
| X Test structure | The view's tests extend `tests/test_views.py`; the component's go in `tests/test_components/test_drf_stripe.py`, already declared as a non-mirror path | Pass |
| XI Cohesion | The view is one class with one method, beside the sibling it mirrors. No new module of loose functions | Pass |
| XII Interface layer | The page renders a mount point and reads two settings. It computes no charge, reaches no provider from the server, and adds no model, form, admin or serializer. Mounting a provider's embed is named in this article as allowed and expected | Pass |
| XIII No backend dependency | No import of the backend; no script element emitted; the publishable key reaches the component as an attribute. **The article's sentence forbidding a settings read is narrowed to the component by this feature** — see Complexity Tracking and `decisions.md` | Pass, with the amendment |
| XIV Installation, not configuration | Unchanged. The page exists because the backend is installed; the identifier and key are configuration the page *reads*, and without them the page still renders and says so | Pass |
| XV One namespace per backend | Everything that knows what a pricing table is lives under `cotton/drf_stripe/` and the namespace's own view. Nothing is shared with a hypothetical second provider | Pass |
| XVI Rendered output is a contract | The whole feature. The element and each attribute are asserted in rendered markup; the absent-value state is asserted as a sentence a reader sees; no amount is produced by this package at all | Pass |
| XVII Compatibility | A new component, a new view and two new optional settings are additive. Absent settings are the documented first-run state, not a break | Pass |

## Project Structure

### Documentation (this feature)

```text
specs/003-pricing-table/
├── spec.md              # merged to main at the spec gate
├── decisions.md         # merged with it; appended to here
├── plan.md              # this file
├── research.md          # what was read in the dependency and the provider's guide
├── tasks.md             # the task graph
├── progress.md          # run narrative
└── feature-state.json   # the ledger
```

No `data-model.md` and no `contracts/`: the feature defines no data, and the rendered page is the
contract Article XVI already says how to assert.

### Source code

```text
mvp_payments/
├── views.py                                  # PlansPageView beside SubscriptionPageView
├── namespaces/drf_stripe.py                  # the Plans page names the new view
├── static/mvp_payments/drf_stripe/
│   └── pricing_table.js                      # new — reveals the message when the library is absent
└── templates/
    ├── mvp_payments/drf_stripe/plans.html    # the page: the component, or the sentence
    └── cotton/drf_stripe/
        ├── pricing_table.html                # new — the provider's element and its attributes
        └── plans_unavailable.html            # new — the sentence shown instead

tests/
├── test_views.py                             # extended: the page's context and its two states
├── test_components/test_drf_stripe.py        # extended: the component, standalone
└── test_app.py                               # extended: no script element in any shipped template

demo/
├── settings.py                               # a pricing table identifier and publishable key
├── templates/base.html                       # the provider's library, in an overridable block
├── templates/demo/home.html                  # the component on a page of the project's own
├── templates/demo/plans_unconfigured.html    # the page template with nothing supplied
├── templates/demo/no_library.html            # the component with the library block emptied
├── urls.py, views.py                         # the two demonstration routes above
└── management/commands/seed_demo.py          # unchanged; the accounts already exist

docs/
└── plans-page.md                             # new — the component, its attributes, the settings

CONSTITUTION.md                               # Articles XII and XIII narrowed to the component
CHANGELOG.md                                  # the entry
README.md                                     # the link to docs/plans-page.md
```

**Structure Decision**: no new Python module. The view is nine lines beside the one it mirrors, and
a module for it would separate two classes that are read together. `plans_unavailable.html` is a
component rather than markup inside the page template so that a project overriding the page keeps
the sentence, and so it can be asserted standalone.

## Design

### The component

`cotton/drf_stripe/pricing_table.html`, reached as `<c-drf-stripe.pricing-table>`, declaring:

```
<c-vars table_id publishable_key customer_email />
```

It emits `<stripe-pricing-table>` carrying `pricing-table-id` and `publishable-key`, plus
`customer-email` when there is an address to carry. It emits no script element, no style, and
nothing else except the hidden failure message and the marker `pricing_table.js` looks for.

**Where the address comes from (FR-005).** `customer_email` wins when the caller supplied it.
Otherwise the component reads `request.user` from the context — the precedent is
`portal_link.html`, which already reads `csrf_token` the same way — and uses that person's email
address when they are signed in and hold one. Where there is neither, the attribute is omitted
entirely rather than emitted empty, because an empty `customer-email` is not the same instruction
to the provider as an absent one.

The component reads no settings (FR-003) and imposes no sign-in requirement (FR-006, FR-009), so
the same placement works on a public landing page.

### The page

`PlansPageView` subclasses `PaymentPageView`, exactly as `SubscriptionPageView` does, and adds two
names to the context — the documented surface FR-012 and US-5 scenario 2 promise:

| Name | What it is |
|---|---|
| `pricing_table_id` | `settings.MVP_PAYMENTS["DRF_STRIPE_PRICING_TABLE_ID"]`, or `None` |
| `publishable_key` | `settings.MVP_PAYMENTS["DRF_STRIPE_PUBLISHABLE_KEY"]`, or `None` |

Both are read at render time through `getattr(settings, "MVP_PAYMENTS", {})`, never at import
(Article XIV). The drf-stripe contribution names the view on its Plans page; nothing else about how
that page arrives changes.

`plans.html` renders the component when both values are present, and `<c-drf-stripe.plans-unavailable />`
when either is absent (FR-007). The page keeps `LoginRequiredMixin` through `PaymentPageView`
(FR-008), which is inherited rather than restated.

### Telling a reader the library never arrived

The provider's element renders as nothing when its library has not loaded, and there is no event to
listen for. `pricing_table.js` checks one thing, after `load`:

```js
customElements.get("stripe-pricing-table")
```

Undefined means the project did not load the library, or the reader's browser could not reach the
provider's origin — the two conditions US-4 scenario 3 and the specification's last edge case name.
The component's hidden message is then revealed. Defined means the element is the provider's to
render, including when it renders an error of its own, which this package does not interpret.

The file is loaded the way the project already loads static assets, with no build step
(Article XIII). The demo loads it beside the provider's library.

### What the demonstration project shows

Every state the specification names has to be reachable by opening a page:

- **Plans page, configured** — demo settings carry a pricing table identifier and publishable key,
  and `base.html` loads the provider's library from the provider's own network in a
  `{% block provider_library %}`, labelled a demonstration convenience.
- **The component on a project's own page** — `demo/home.html` places it directly, so it is on a
  page reachable without signing in (US-3).
- **Nothing configured** — a demo route rendering the package's page template with neither value in
  its context (US-4 scenarios 1 and 2).
- **Library never loaded** — a demo route whose template empties `provider_library`, so the element
  is emitted and never comes to life (US-4 scenario 3).

These are the demonstration project's routes, not the package's. Nothing in `mvp_payments/` knows
they exist.

### The constitution amendment

Two sentences currently say a publishable key is "never read from Django settings" by this package.
Applied literally the shipped page cannot work, because nobody is passing it attributes — which is
the point of a page a project does not build. Both are narrowed to the component, whose freedom
from hidden configuration is the property those sentences exist to protect:

- Article XII, the "No secret keys" bullet.
- Article XIII, the paragraph on wrapping a provider's embed.

The reasoning is already recorded in `decisions.md` and is not repeated in the constitution. This
amendment lands in this feature's pull request, as the specification's Assumptions require.

## Phases

No foundational phase: nothing shared is built before the first story. The demo's accounts already
exist and no factory is needed, because this feature reads no record.

Stories in priority order, one at a time, in a single worktree:

- **US-1** — the component, `PlansPageView`, the contribution naming it, `plans.html`, the demo's
  settings and library block, and `docs/plans-page.md` with the component and the settings. The
  documentation task belongs to this story because this is where the public names appear.
- **US-2** — the address: the attribute, the signed-in fallback, and the three cases where nothing
  is carried.
- **US-3** — the component on a page of the project's own, for a reader who is not signed in, and
  the demo's landing-page placement.
- **US-4** — `plans_unavailable.html`, the page's branch, `pricing_table.js`, the hidden message,
  and the two demonstration routes.
- **US-5** — the override tests (component, then page template), the documented context names in
  `docs/plans-page.md`, the README link, the CHANGELOG entry and the constitution amendment.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| Narrowing two constitution sentences | The shipped Plans page has no template author to pass it attributes, so read literally the sentences make the feature's primary story impossible | A page that renders nothing until a project subclasses its view defeats the goal the page exists for — a working page arriving without the project building one |
| A second static JavaScript file | An undefined custom element emits no event and renders as an empty box, so the only way to tell a reader is to check for the element's definition in the browser | A server-side check cannot know what the browser loaded; a timing-based check on whether the table painted would claim to detect states the specification leaves to the provider |
| The component reads `request.user` from context | FR-005 requires the signed-in person's address, and the shipped page is not the only placement that should get it | Passing the address down from the view would leave a project's own placement without it, and FR-005 puts the fallback in the component deliberately |
