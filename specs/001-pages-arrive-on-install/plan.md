# Implementation Plan: Payment pages that appear when you install a backend

**Branch**: `feat/001-pages-arrive-on-install` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-pages-arrive-on-install/spec.md`

## Summary

A namespace declares what it contributes to the Account Center — its pages, its navigation entries
and its card — as one object. The application's `ready()` registers the entries of every
contribution whose backend is in `INSTALLED_APPS`, the package's URL configuration mounts the same
set's pages, and an overridden overview template renders the same set's cards through a template
tag. One condition, `apps.is_installed(...)`, decides all three, so the three surfaces cannot drift
apart. The card carries a second condition of its own, because a link it renders must resolve or
the page it sits on fails.

The drf-stripe namespace declares three pages — subscription, plans and billing — each a
login-required view over django-mvp's page classes, rendering a heading inside the Account Center
layout. Filling them is R2, R3 and R5.

## Technical Context

**Language/Version**: Python 3.12+ (CI matrix 3.12 and 3.13; the development virtualenv is 3.14)

**Primary Dependencies**: Django 5.2 and 6.0, django-mvp 0.23.0. No payment backend, now or ever —
`tests/test_app.py` asserts the runtime dependency set is exactly `{django, django-mvp}`.

**Development-only dependencies added here**: `drf-stripe-subscription` and `stripe <8`, for the
demo project and the test suite. See `research.md` for why the bound is needed and why it reaches
no consumer.

**Storage**: none. The package defines no model and ships no migration.

**Testing**: pytest with pytest-django, settings inherited from `demo/settings.py` by
`tests/settings.py`. Assertions are made against rendered output, never against class names
(Article XVI).

**Target Platform**: a Django project that has installed django-mvp.

**Project Type**: installable Django application — templates, a small amount of routing Python, no
data.

**Constraints**: nothing at import time may touch the application registry, reverse a URL or read
settings (Article XIV). `mvp_payments` must precede `mvp` in `INSTALLED_APPS` for its template
override to resolve.

**Scale/Scope**: one namespace, three pages, one card, five user stories.

## Constitution Check

Read before planning and re-checked after the design below.

| Article | Bearing on this feature | Verdict |
|---|---|---|
| I Test-First | Every behaviour here is observable through a rendered page or a menu, so every task is testable before it is written | Pass |
| II Simplicity / III Anti-Abstraction | One class, `Contribution`, and one instance of it. It is not a base class and nothing subclasses it. It exists because the specification names the concept and because three surfaces must agree on one condition | Pass |
| VI Documentation | README install order corrected, what appears documented, CHANGELOG entry, the superseded working notes removed | Pass |
| VII Dependency discipline | No runtime dependency added. Two development dependencies, justified in `research.md` | Pass |
| VIII Internationalization | Every label, page title and card string is wrapped for translation | Pass |
| IX Data-model conventions | No model, no field, no migration | Not applicable |
| X Test structure | Test modules mirror the source tree; a suite whose subject is not a Python module is declared under `[tool.forge.conformance] non-mirror-paths` | Pass |
| XI Cohesion | The namespace's behaviour is grouped on `Contribution`. The template tag module is a framework-dictated shape and an explicit exception | Pass |
| XII Interface layer | **Amended by this feature.** The restriction of every view to a template-rendering one is lifted; views are built on django-mvp's view classes. Everything else the article forbids is unchanged and still asserted by `tests/test_app.py` | Amended, see Complexity Tracking |
| XIII No backend dependency | No backend declared, none imported. A contribution names its backend by application label, a string | Pass |
| XIV A page appears because two apps are installed | The whole feature. Gate on installation, register in `ready()`, use django-mvp's published extension points, and an unreachable entry is already hidden by django-flex-menus | Pass |
| XV One namespace per backend | `Contribution` carries no cross-backend behaviour. Two namespaces share the registration mechanism and nothing about what a page means | Pass |
| XVI Rendered output is a contract | Every page, entry and card has a test asserting rendered output. No amount is rendered anywhere in this feature | Pass |

## Project Structure

### Documentation (this feature)

```text
specs/001-pages-arrive-on-install/
├── spec.md              # merged to main at the spec gate
├── decisions.md         # merged with it; appended to here
├── plan.md              # this file
├── research.md          # what was read from the dependencies
├── tasks.md             # the task graph
├── progress.md          # run narrative
└── feature-state.json   # the ledger
```

No `data-model.md`: the feature has no data. No `contracts/`: the rendered page is the contract and
Article XVI already says how it is asserted.

### Source code

```text
mvp_payments/
├── apps.py                                  # ready() registers available contributions
├── contributions.py                         # Contribution and Page — what a namespace declares
├── namespaces/
│   ├── __init__.py                          # the declared contributions, in one tuple
│   └── drf_stripe.py                        # the drf-stripe contribution
├── urls.py                                  # application namespace "payments"; pages of available contributions
├── views.py                                 # the page view
├── templatetags/
│   └── mvp_payments.py                      # renders the cards of available contributions
└── templates/
    ├── mvp/account/overview.html            # adds to account.cards through {{ block.super }}
    └── mvp_payments/
        ├── card.html                        # one contribution's card
        └── drf_stripe/
            ├── subscription.html
            ├── plans.html
            └── billing.html

tests/
├── test_app.py                              # extended: absence, dependencies, imports
├── test_contributions.py
├── test_urls.py
├── test_views.py
├── test_templatetags/
│   └── test_mvp_payments.py
├── test_namespaces/
│   └── test_drf_stripe.py
├── second_namespace/                        # a second contribution, for User Story 5
├── settings_without_backend.py              # the same settings with the backend removed
└── urls_without_payments.py                 # the project's URLs without this package's include

demo/
└── settings.py                              # installs the backend and mounts its URLs
```

**Structure Decision**: the layout follows the package's existing shape — a flat application with
templates under `mvp_payments/templates/` — and adds one subpackage, `namespaces/`, so that a second
backend is a new file beside the first rather than an edit to a shared one. That is Article XV
expressed as a directory.

## Design

### What a namespace declares

`Contribution` is a frozen dataclass holding the backend's application label, the namespace slug,
its pages and its card. `Page` holds a slug, a URL name, a label, an icon and a template. Neither
constructs a `MenuItem`: building one attaches it to the global menu tree immediately, which
Article XIV forbids at import time. Entries are built inside `register()`.

Four methods, one condition for the three surfaces and a second one the card alone needs:

- `is_available()` — `apps.is_installed(self.backend_app_label)`, and nothing else. `ready()` and
  the URL configuration both call it, and neither may reverse a URL.
- `is_reachable()` — this namespace's pages reverse. Only a render-time caller may ask, and the
  card is the one that has to (D3).
- `register()` — extends `AccountCenterMenu` with one `MenuItem` per page.
- `url_patterns()` — one `path()` per page, named `<namespace slug>-<page slug>`.

`namespaces/__init__.py` holds the declared contributions in one tuple and a function returning the
available ones. Everything else reads that function, so the three surfaces cannot disagree about
what is installed.

### Where each surface comes from

- **Entries**: `MvpPaymentsConfig.ready()` calls `register()` on every available contribution.
- **Pages**: `mvp_payments/urls.py` sets `app_name = "payments"` and collects `url_patterns()` from
  every available contribution. A project includes this module once.
- **Card**: `mvp_payments/templates/mvp/account/overview.html` extends the same name, keeps
  `{{ block.super }}` and calls the tag that renders one card per available contribution.

### The view

One view class, over `LoginRequiredMixin` and django-mvp's `MVPTemplateView`, following
`AccountCenterView`'s shape. It takes its title and template from the `Page` it is constructed for,
so the three pages are three instances rather than three classes with one line each.

### Repeated registration

`ready()` can run more than once in a process — an autoreloading development server is the usual
way — and `AccountCenterMenu` is a module-level tree that survives it, so entries accumulate. The
registration checks for its own entries by name before adding them, and a test asserts that
registering twice renders the navigation once.

## Phases

**Foundational** (sequential, before any story): development dependencies; the backend installed and
its URLs mounted in the demo; the standards document's Article XII amended; the superseded working
notes and the reference to them removed.

Then the stories, in priority order: US-1, US-2, US-3, US-4, US-5, dispatched one at a time into a
single worktree rather than in parallel. US-1 builds the mechanism, the pages and the navigation;
US-3 builds the card; US-2, US-4 and US-5 are largely the tests that hold the guarantees, with
whatever code each one turns out to need.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| Article XII amended to allow views beyond template rendering | The repository owner lifted the restriction at intake. A page that will show a person their own subscription cannot be a template with no view behind it | Keeping the restriction would have made R2, R3 and R5 impossible to build in this package at all, which was the reason it was lifted |
| A `Contribution` class with one instance | Three surfaces must agree on one condition, and the specification names the concept in its own glossary | Three independent `is_installed` checks — rejected because they drift, and a drift of that kind renders an entry whose page does not exist |
