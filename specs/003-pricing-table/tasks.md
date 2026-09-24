# Tasks — 003 Offer plans through the provider's own pricing table

**Branch**: `feat/003-pricing-table` · **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Test-first throughout, per Article I: every task that changes behaviour writes its failing test
first. `[P]` marks tasks that touch disjoint files and may run in parallel within their phase.

Per-task test scope is the module or template the task touches. The full suite runs once per story,
at the story's report.

Assertions are made against rendered output, never against the presence of a class name
(Article XVI). For this feature that means the element's tag and each of its attributes, read out
of the rendered markup.

Stories are dispatched in order, each starting from the branch the previous one left. US-1 builds
the component, the view and the page; every story after it adds to what US-1 left behind.

No foundational phase. This feature reads no record, so there is nothing to seed before the first
story and no factory to write.

## Phase 1 — US-1: Plans arrive on the page without building one (P1) → #27

### Tests first

- **T001** `tests/test_components/test_drf_stripe.py::TestPricingTable` — rendering
  `<c-drf-stripe.pricing-table table_id="..." publishable_key="..." />` in a bare template produces
  a `stripe-pricing-table` element carrying `pricing-table-id` and `publishable-key` with those
  values; the output contains no `<script` anywhere; the output contains no digit that could read
  as an amount, because this component produces none (FR-011, SC-007). Red before T005.
- **T002** [P] `tests/test_views.py::TestPlansPage` — a signed-in person's Plans page carries
  `pricing_table_id` and `publishable_key` in its context, read from `settings.MVP_PAYMENTS`, and
  renders the provider's element carrying both (US-1 scenario 1); the rendered page contains no
  `<script` referencing the provider (US-1 scenario 2, SC-002); a visitor who is not signed in is
  redirected to the sign-in page (US-1 scenario 5, FR-008). Use `override_settings` for the two
  values. Narrow the element assertion to the page's content region with `tests/markup.py`, because
  "Plans" is also a navigation label. Red before T006 and T007.
- **T003** [P] `tests/test_views.py::TestPlansPage` — the context names are read at render time, not
  at import: the page renders correctly when `MVP_PAYMENTS` is absent from settings entirely, and
  importing `mvp_payments.views` with no settings configured raises nothing (Article XIV). Red
  before T006.
- **T004** [P] `tests/test_app.py` — extend the existing shipped-templates assertion so that no
  template under `mvp_payments/templates/` contains a `<script` element with a `src` pointing at any
  host (Article XIII, FR-002). This is the repository-wide guarantee behind SC-002 and it must hold
  for every template added by this feature and every one added after it. Red before T005 only in the
  sense that it must exist before the component does.

### Then the code

- **T005** `mvp_payments/templates/cotton/drf_stripe/pricing_table.html` — the component. Declares
  `<c-vars table_id publishable_key customer_email />` and emits `<stripe-pricing-table>` with
  `pricing-table-id` and `publishable-key`. `customer_email` is wired in US-2; here it is declared
  and not yet read, so this task emits neither an empty nor a populated `customer-email`. Header
  comment in the shape `portal_link.html` uses: what the component is, its props, and why no script
  element is emitted.
- **T006** `mvp_payments/views.py` — `PlansPageView(PaymentPageView)`, beside `SubscriptionPageView`
  and following its shape. `get_context_data` adds `pricing_table_id` and `publishable_key` from
  `getattr(settings, "MVP_PAYMENTS", {})`, each defaulting to `None`. Docstring names both context
  entries and says they are the surface a project overriding the page relies on.
- **T007** `mvp_payments/namespaces/drf_stripe.py` — the Plans `Page` names `PlansPageView`. Update
  the module docstring, which currently says filling these pages in is a later roadmap item.
- **T008** `mvp_payments/templates/mvp_payments/drf_stripe/plans.html` — render
  `<c-drf-stripe.pricing-table>` with the two context values. The unavailable branch arrives in
  US-4; here the page renders the component unconditionally.
- **T009** [P] `demo/settings.py` — add `DRF_STRIPE_PRICING_TABLE_ID` and
  `DRF_STRIPE_PUBLISHABLE_KEY` to `MVP_PAYMENTS`, with clearly-fake test values beside the existing
  fake backend keys and a comment saying they are a demonstration's, not a project's.
- **T010** [P] `demo/templates/base.html` — a `{% block provider_library %}` loading
  `https://js.stripe.com/v3/pricing-table.js` and `pricing_table.js`, with a comment saying the
  provider forbids self-hosting and that choosing to load it is the project's decision, not this
  package's (Article XIII). A block, because US-4 needs a page that empties it.
- **T011** `docs/plans-page.md` — new. The component, its three attributes, the two settings the
  page reads, and the project's responsibility for loading the provider's library. The context names
  and the override instructions arrive in US-5; this task writes everything a project needs to make
  the page work (FR-013). The verify docs step reads the branch's diff at every story exit, so the
  page that introduces these public names carries their documentation.

### Story exit

Full suite, lint, typecheck, build, conformance, docs. Report against US-1's four testable
acceptance scenarios; scenarios 3 and 4 are the provider's behaviour in a browser and are covered
by the walkthrough, not by a test.

## Phase 2 — US-2: A purchase belongs to the person who made it (P1) → #28

### Tests first

- **T012** `tests/test_components/test_drf_stripe.py::TestPricingTable` — rendered for a signed-in
  person holding an email address, the element carries `customer-email` with that address
  (scenario 1); for a signed-in person with no address, no `customer-email` attribute appears at
  all, and the rest of the element is unchanged (scenario 2); for an anonymous visitor, none appears
  (scenario 3); given `customer_email` as an attribute, that value is used in preference to the
  signed-in person's (scenario 4). Assert the attribute's absence as absence, not as emptiness. Red
  before T014.
- **T013** [P] `tests/test_views.py::TestPlansPage` — the Plans page rendered for a signed-in person
  carries their own address on the element, end to end through the page rather than the component
  alone (FR-005, SC-003). Red before T014.

### Then the code

- **T014** `mvp_payments/templates/cotton/drf_stripe/pricing_table.html` — read `customer_email`,
  falling back to the context's `request.user` when that person is authenticated and holds an
  address, and omitting the attribute entirely when there is neither. Extend the header comment with
  why the address is passed at all: the backend matches a provider customer to an application user
  by email address alone, so a purchase made under another address attaches to nobody
  (`research.md`).
- **T015** [P] `docs/plans-page.md` — document the address: where it comes from, that an attribute
  wins, and what the absence means for a purchase.

### Story exit

Full suite and the machine gates. Report against all four acceptance scenarios.

## Phase 3 — US-3: The same plans on a page of the project's own (P2) → #29

### Tests first

- **T016** `tests/test_components/test_drf_stripe.py::TestPricingTable` — the component rendered in
  a template unrelated to any page of this package, for an anonymous visitor, produces the complete
  element from its attributes alone (scenarios 1 and 2); rendering it requires no view, no context
  processor and no query — assert with `django_assert_num_queries(0)` around a render carrying only
  the attributes (scenario 3). Red before T017, which is only a demonstration; the component itself
  may already satisfy this, and a test that passes on first run here is evidence the design held,
  recorded as such rather than forced red.
- **T017** [P] `tests/test_demo.py` — the demo's landing page carries the element for an anonymous
  visitor.

### Then the code

- **T018** `demo/templates/demo/home.html` — place `<c-drf-stripe.pricing-table>` with the demo's
  values, on the page a visitor reaches without signing in, with a line of copy saying this is the
  same component the Account Center's Plans page renders.

### Story exit

Full suite and the machine gates. Report against all three acceptance scenarios, and state plainly
whether T016 was red before T018 or passed on first run.

## Phase 4 — US-4: Nothing to show yet, said plainly (P2) → #30

### Tests first

- **T019** `tests/test_views.py::TestPlansPage` — with no pricing table identifier configured, the
  page states that plans cannot be shown and its rendered output contains no `stripe-pricing-table`
  element (scenario 1); the same with no publishable key (scenario 2); with `MVP_PAYMENTS` absent
  altogether, nothing raises and the rest of the page — its heading, the account navigation —
  renders unchanged (scenario 4). Red before T022 and T023.
- **T020** [P] `tests/test_components/test_drf_stripe.py::TestPlansUnavailable` — the unavailable
  component renders its sentence standalone and takes no props. Red before T021.
- **T021** [P] `tests/test_components/test_drf_stripe.py::TestPricingTable` — the pricing table
  component renders a `hidden` element carrying the could-not-be-loaded message and the marker
  `pricing_table.js` binds to; the message is present in the markup and hidden, never absent, so
  revealing it needs no string from JavaScript (scenario 3, FR-010). Red before T024.

### Then the code

- **T022** `mvp_payments/templates/cotton/drf_stripe/plans_unavailable.html` — the sentence. Takes
  no props. Follows `no_subscription.html`'s shape, using django-mvp's empty-state component so it
  reads as part of the page rather than as an error.
- **T023** `mvp_payments/templates/mvp_payments/drf_stripe/plans.html` — branch: the component when
  both values are present, `<c-drf-stripe.plans-unavailable />` otherwise.
- **T024** `mvp_payments/templates/cotton/drf_stripe/pricing_table.html` — add the hidden message and
  its marker, in the shape `portal_link.html` already uses for its failure message.
- **T025** `mvp_payments/static/mvp_payments/drf_stripe/pricing_table.js` — after `load`, reveal the
  hidden message wherever `customElements.get("stripe-pricing-table")` is undefined. No build step,
  no bundler, and a comment naming what the file looks for and why a timing-based check was rejected
  (`research.md`).
- **T026** [P] `demo/views.py`, `demo/urls.py`, `demo/templates/demo/plans_unconfigured.html`,
  `demo/templates/demo/no_library.html` — two demonstration routes: the package's page template
  rendered with neither value in its context, and the component rendered on a page whose
  `provider_library` block is empty. Both are the demonstration project's, and nothing in
  `mvp_payments/` knows they exist. Link both from the demo's landing page so every state is
  reachable by clicking.
- **T027** [P] `docs/plans-page.md` — document both states: what a reader sees before the project has
  configured anything, and what they see when the library never arrived.

### Story exit

Full suite and the machine gates. Report against all four acceptance scenarios.

## Phase 5 — US-5: A project supplies its own markup instead (P3) → #31

### Tests first

- **T028** `tests/test_views.py::TestPlansPageOverride` — with a project template directory ahead of
  the package's, a project's own `cotton/drf_stripe/pricing_table.html` is what the Plans page
  renders (scenario 1); a project's own `mvp_payments/drf_stripe/plans.html` likewise, and every
  context name the shipped page would have used is available to it (scenario 2); either override
  renders with no view of the project's own and no query (scenario 3). Follow
  `tests/settings_with_project_template_override.py`, which already establishes how an override is
  tested here. Red before T030 only where a fix is needed; an override that works on first run is
  evidence the design held.
- **T029** [P] `tests/test_app.py` — the documentation page is reachable from the README, asserted
  the way the existing documentation links are.

### Then the code

- **T030** `docs/plans-page.md` — complete it: the two context names as a table, how to override the
  component, how to override the page template, and what each override keeps. This is US-5
  scenario 4 and FR-013.
- **T031** [P] `README.md` — link `docs/plans-page.md` from the documentation section, beside the
  subscription page's.
- **T032** [P] `CONSTITUTION.md` — narrow the two sentences that forbid reading a publishable key
  from settings, so each applies to a component rather than to the whole package: the "No secret
  keys" bullet in Article XII, and the embed paragraph in Article XIII. The page reading settings
  and passing them down is named as the permitted shape. No reasoning in the constitution itself —
  it is in `decisions.md`, which is where the amendment's justification belongs.
- **T033** [P] `CHANGELOG.md` — one `[Unreleased]` entry under Added: the component, the page's two
  settings, and the documentation page.

### Story exit

Full suite and the machine gates. Report against all four acceptance scenarios.

## Convergence

After the last story: the migration consolidation step is not applicable (no migration), the
cleanup pass applies `craft-simplify` to the whole feature diff, the ADR verdict is recorded for
every decision in `decisions.md`, and the story comments are checked.

The constitution amendment is a candidate for an ADR on its own reading — it is durable, it is
cross-cutting, and its reasoning is not obvious from the diff. Decide that at S5 against the bar,
not here.
