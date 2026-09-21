# Tasks — 001 Payment pages that appear when you install a backend

**Branch**: `feat/001-pages-arrive-on-install` · **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Test-first throughout, per Article I: every task that changes behaviour writes its failing test
first. `[P]` marks tasks that touch disjoint files and may run in parallel within their phase.

Per-task test scope is the class or module the task touches. The full suite runs once per story, at
the story's report.

Assertions are made against rendered output, never against the presence of a class name
(Article XVI).

## Phase 0 — Foundational

Everything here has to exist before the first story. T001 and T002 are US-1's prerequisites;
T003 and T004 are FR-013's documentation corrections, which belong to no story and are carried in
US-1's ledger entry because US-1 is what makes them necessary.

Every story after US-1 builds on what US-1 leaves behind, and US-4 additionally needs the card
US-3 builds. Stories are therefore dispatched in order, one worktree at a time, rather than in
parallel. No story edits a file an earlier story created, which is the property that matters at
convergence.

- **T001** `pyproject.toml`, `poetry.lock` — add `drf-stripe-subscription` and `stripe <8` to the
  development group. The bound on `stripe` is not optional: the backend imports
  `stripe.error.StripeError`, removed at version 8, so mounting its URL configuration raises
  without it (`research.md`). Confirm `poetry check` and a clean install, and confirm the runtime
  dependency list is untouched.
- **T002** `demo/settings.py`, `demo/urls.py` — install `rest_framework` and `drf_stripe`, mount the
  backend's URL configuration, and add the `DRF_STRIPE` block the demo needs. Leave `mvp_payments`
  where it is, above `mvp`: the template override in US-3 depends on that order. Apply the
  backend's migrations to the demo database.
- **T003** `CONSTITUTION.md` — amend Article XII. The sentence restricting a view to one that hands
  a template to the renderer goes, and the paragraph around it is rewritten to say that a page may
  have whatever view it needs, built on django-mvp's view classes. Everything else the article
  forbids stays exactly as written: no models, no migrations, no forms or admin or serializers, no
  payment logic, no card fields, no secret keys, no server-side calls to a provider, no trust in
  what a backend returns. Bump the amendment date.
- **T004** [P] `docs/brainstorm.md`, `AGENTS.md` — delete the working-notes document and the
  paragraph in `AGENTS.md` that points at it. Its argument that this package ships no Python beyond
  an application configuration is superseded by T003.

## Phase 1 — US-1: The backend's pages are simply there (P1) → #9

### Tests first

- **T005** `tests/test_contributions.py::TestContribution` — a contribution reports itself available
  when its backend's application label is installed and unavailable when it is not;
  `url_patterns()` returns one route per declared page, each named `<namespace>-<page>`;
  `register()` adds exactly one navigation entry per page. Assert the exact entry count, not that
  entries exist. Red before T010.
- **T006** [P] `tests/test_contributions.py::TestRepeatedRegistration` — calling `register()` twice
  leaves the Account Center navigation rendering each entry once. A development server reloads and
  runs `ready()` again, and the menu tree survives that, so accumulation is the default failure.
  Red before T010.
- **T007** [P] `tests/test_urls.py::TestPaymentURLs` — each of the three page names reverses under
  the `payments` application namespace and resolves to a page view; a name belonging to no declared
  page does not reverse. Red before T013.
- **T008** [P] `tests/test_views.py::TestPaymentPage` — a signed-in request to each page renders it
  inside the Account Center layout, carrying that page's heading and the Account Center's
  navigation; an anonymous request is redirected to the project's sign-in location. Assert the
  heading text from the rendered body. Red before T012.
- **T009** [P] `tests/test_namespaces/test_drf_stripe.py::TestDrfStripeContribution` — the
  contribution names the backend's application label, declares exactly three pages with the
  expected slugs and translatable labels, and a signed-in request to the Account Center renders one
  navigation entry per page. Red before T011.

### Implementation

- **T010** `mvp_payments/contributions.py` — `Page` and `Contribution` as frozen dataclasses.
  `Contribution` carries the backend's application label, the namespace slug, its pages and its
  card template, and exposes `is_available()`, `is_reachable()`, `register()` and
  `url_patterns()`. `is_available()` asks the application registry and nothing else, because
  `ready()` and the URL configuration both call it and neither may reverse a URL.
  `is_reachable()` is the second half — this namespace's pages reverse — and only a render-time
  caller may use it (D3). No `MenuItem` is constructed at import time: building one attaches it to
  the global tree, which Article XIV forbids before the application is ready. `register()` is
  idempotent by entry name.
- **T011** `mvp_payments/namespaces/__init__.py`, `mvp_payments/namespaces/drf_stripe.py` — the
  drf-stripe contribution, declaring the subscription, plans and billing pages with translatable
  labels and icons resolvable through the packaged icon set. `__init__` holds the declared
  contributions in one tuple and the function that returns the available ones. Every other module
  reads that function rather than testing `is_installed` for itself.
- **T012** `mvp_payments/views.py` — one page view over `LoginRequiredMixin` and django-mvp's
  `MVPTemplateView`, following `AccountCenterView`'s shape, taking its template and title from the
  `Page` it is built for.
- **T013** `mvp_payments/urls.py` — `app_name = "payments"`, routes collected from every available
  contribution. This is the module a project includes once.
- **T014** Templates — `mvp_payments/templates/mvp_payments/drf_stripe/{subscription,plans,billing}.html`,
  each extending `mvp/account/base.html` and filling its content block with the page's heading and
  nothing else. No placeholder copy about content arriving later.
- **T015** `mvp_payments/apps.py` — `ready()` registers every available contribution, and does
  nothing else.
- **T016** [P] `demo/urls.py` — mount `mvp_payments.urls`, so the demo shows the pages arriving.
- **T017** Documentation — correct the README's installation order: `mvp_payments` goes **before**
  `mvp` in `INSTALLED_APPS`, because the template override in US-3 resolves through application
  order and the current instruction silently disables it. Document the single include line and what
  appears as a result. Add *contribution* to `CONTEXT.md`'s glossary — the specification's Key
  Entities introduce the term and the glossary is where this project pins its vocabulary. Add the
  changelog entry.

## Phase 2 — US-2: A backend you have not installed costs you nothing (P1) → #10

### Tests first

- **T018** `tests/settings_without_backend.py` — the project's settings with the backend removed
  from the installed applications, for the tests below to run against.
- **T019** `tests/test_app.py::TestNothingWithoutABackend` — with the backend absent, the Account
  Center renders, no navigation entry and no card belonging to it appear, and none of its page
  addresses resolve. Assert against the rendered navigation, not against the menu objects.
- **T020** [P] `tests/test_app.py` — extend the existing import and dependency assertions to cover
  the modules this feature adds: the declared runtime dependencies stay exactly Django and
  django-mvp, and no module in the package imports a payment backend or a provider's library. The
  existing assertions already walk the package, so confirm they reach `namespaces/` and
  `templatetags/` rather than assuming they do.

### Implementation

- **T021** Whatever the tests above expose. The expectation is nothing: availability is decided in
  one place and every surface reads it. A leak here means a surface tested `is_installed` for
  itself, and the fix is to route it through the one function rather than to special-case it.

## Phase 3 — US-3: The overview says what is available (P2) → #11

### Tests first

- **T022** `tests/test_templatetags/test_mvp_payments.py::TestPaymentCards` — the tag renders one
  card per available contribution and nothing for an unavailable one. Assert the rendered card's
  heading and its link target.
- **T023** [P] `tests/test_views.py::TestAccountCenterOverview` — a signed-in request to the Account
  Center overview carries exactly one card for the installed backend, leading into that backend's
  pages, and the cards django-mvp or another application contributed are still there. The second
  half is what proves `{{ block.super }}` was kept.

### Implementation

- **T024** `mvp_payments/templatetags/mvp_payments.py` — the tag, rendering the card of each
  contribution that is both available and reachable. Both halves are on `Contribution` already
  (T010), so the tag asks rather than decides. A registered template tag module is an explicit
  exception to Article XI, so this is not a structural deviation.
- **T025** `mvp_payments/templates/mvp/account/overview.html`,
  `mvp_payments/templates/mvp_payments/card.html` — the override extends the same template name,
  keeps `{{ block.super }}` and calls the tag. The card carries a translatable heading and a link
  into the namespace's first page.
- **T026** [P] Documentation — the card in the README's description of what installing a backend
  produces, and the `INSTALLED_APPS` order stated as the requirement it is rather than a
  suggestion.

## Phase 4 — US-4: Nothing is offered that cannot be reached (P3) → #12

### Tests first

- **T027** `tests/test_views.py::TestURLsNotMounted` — with the backend installed and this package's
  URL configuration not mounted, a signed-in request to the Account Center renders, no entry
  belonging to the backend appears, **and no card belonging to it appears either**, and nothing
  raises. The navigation half is already handled by django-flex-menus, which hides a leaf whose URL
  will not reverse (`research.md`). The card half is not: a card rendering a link through `{% url %}`
  raises `NoReverseMatch` and takes the whole page down with it. The state is built with
  `tests/urls_without_payments.py` — the project's URL configuration with this package's include
  removed — selected per test with `override_settings(ROOT_URLCONF=...)`. Red before T028.

### Implementation

- **T028** No implementation expected. The reachability half of the availability check is built in
  T010 and applied by the tag in T024, so this story's work is the test that makes it a guarantee.
  If the test exposes a gap, the fix belongs on `Contribution` where both halves already live.

## Phase 5 — US-5: A second backend leaves the first alone (P3) → #13

### Tests first

- **T029** `tests/second_namespace/` — a minimal installed application to gate on, and a second
  contribution declared against it, registering through the same mechanism as the real one. This is
  a test fixture for a structural property, not a stand-in for a payment backend.
- **T030** `tests/test_contributions.py::TestNamespaceIndependence` — with both contributions
  available, the first namespace's entries, card and page addresses are identical to what they are
  with only the first installed; no name declared by one namespace resolves to the other's page;
  and no two declared contributions share a URL name. Assert the rendered navigation on both sides,
  not the objects.

### Implementation

- **T031** Whatever the tests above expose. The URL naming scheme already carries the namespace slug
  in every name, so the expectation is that the property holds and the test is what makes it a
  guarantee rather than an accident.
- **T032** [P] Documentation — the README's namespaces section states that a second namespace is
  added beside the first and changes nothing about it.

## Phase 6 — convergence

Not a story. Run after every story is accepted: the full suite, the documentation check, the
simplification pass over the feature's own diff, and the decision verdicts in `decisions.md`.
