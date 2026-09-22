# Tasks — 002 Show a person the subscription they are on

**Branch**: `002-subscription-page` · **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Test-first throughout, per Article I: every task that changes behaviour writes its failing test
first. `[P]` marks tasks that touch disjoint files and may run in parallel within their phase.

Per-task test scope is the class or module the task touches. The full suite runs once per story, at
the story's report.

Assertions are made against rendered output, never against the presence of a class name
(Article XVI).

Stories are dispatched in order, one worktree at a time. US-1 builds the reading, the view and the
page; every story after it adds to what US-1 left behind.

## Phase 0 — Foundational

Nothing in `mvp_payments/` changes here. This phase exists because no story can put a subscription
in front of the page without records to read, and every story needs the same ones.

- **T001** `tests/factories.py` — one `DjangoModelFactory` per backend model the page reads:
  `StripeUserFactory`, `ProductFactory`, `PriceFactory`, `SubscriptionFactory`,
  `SubscriptionItemFactory`, `FeatureFactory`, `ProductFeatureFactory`. Models are resolved with
  `apps.get_model`, never imported, so the test suite obeys the same rule the package does.
  `factory.Sequence` for the identifier primary keys, `factory.SubFactory` for the relations. No
  factory subclass expresses a variant — Article X — and a factory writes no file. Add
  `tests/test_factories.py` asserting each builds a saved row.
- **T002** `tests/conftest.py` — fixtures wrapping those factories: `stripe_user` for the existing
  `user` fixture, `current_subscription` (status `active`, one item, one priced product) and
  `subscriber_client` (a signed-in client whose person holds `current_subscription`). Thin wrappers
  only; a one-off variation is a call to the factory at the call site.
- **T003** [P] `demo/management/commands/seed_demo.py` — extend the command so that after the
  accounts exist it records, for `regular.user`, a Stripe customer, two products with features, one
  active subscription covering two priced items in different currencies, and a second person's
  subscription that must never appear on the first person's page. `staff.user` gets a trialing
  subscription; `super.user` is left with none, so the empty state is reachable without editing
  anything. Idempotent, like the account half already is, and development-only.

## Phase 1 — US-1: The page says what you are subscribed to (P1) → #18

### Tests first

- **T004** `tests/test_money.py::TestMoney` — an amount in a two-decimal currency renders with two
  decimal places and its currency code; a zero-decimal currency (`JPY`) renders as a whole number;
  a three-decimal currency (`BHD`) renders with three; an amount with no currency renders nothing.
  Assert against the rendered string under a known active locale. Red before T008.
- **T005** [P] `tests/test_namespaces/test_drf_stripe_records.py::TestSubscriptionReader` — the
  reader returns one entry per subscription the backend calls current; a subscription the backend
  does not call current is absent; another person's subscription is absent; a person with no
  customer record gets an empty result; a subscription's items each carry their own plan name,
  amount and frequency; the plan's name is the price nickname where set and the product's name
  otherwise. No status string appears in the module under test — assert that too, by driving the
  cases through the backend's own records rather than through a status list of ours. Red before
  T009.
- **T006** [P] `tests/test_contributions.py::TestPageView` — a `Page` built without a view routes to
  `PaymentPageView`; a `Page` given one routes to that view instead. Red before T010.
- **T007** [P] `tests/test_views.py::TestSubscriptionPage` — a signed-in subscriber's page carries
  `subscriptions` in its context and renders, for each, the plan name, the amount with its currency,
  the frequency and the status; a recorded billing period appears; a subscription with no period
  recorded still renders the rest; a subscription covering two items shows both amounts and no third
  figure anywhere; another person's subscription never appears; a status the page has no treatment
  for renders as itself. Assert against rendered output, and assert the absence of a total by
  checking that every figure on the page is one of the recorded amounts. Red before T011.

### Then the code

- **T008** `mvp_payments/money.py` — `Money`, frozen, `minor_units` and `currency`, with the
  exponent table from `research.md`, an `amount` property returning the `Decimal` in the currency's
  own unit, and a `__str__` going through `django.utils.formats.number_format` under the active
  locale. Renders nothing without a currency. Docstrings state why the table is here rather than in
  a dependency.
- **T009** `mvp_payments/namespaces/drf_stripe_records.py` — `PlanFeature`, `Plan`,
  `CurrentSubscription` and `SubscriptionReader.for_user`, exactly as `plan.md` describes. Models
  through `apps.get_model`; `select_related` to the product and `prefetch_related` on its features,
  so one page is a fixed number of queries whatever it holds. Features are read here but rendered in
  US-3.
- **T010** `mvp_payments/contributions.py` — `Page` gains `view: type[PaymentPageView] =
  PaymentPageView`; `url_patterns()` builds each route from `page.view`. No other change to the
  dataclass or to the three surfaces that read it.
- **T011** `mvp_payments/views.py`, `mvp_payments/namespaces/drf_stripe.py` —
  `SubscriptionPageView(PaymentPageView)` putting `subscriptions` into the context through the
  reader, and the drf-stripe contribution naming it for its subscription page.
- **T012** `mvp_payments/templates/cotton/drf_stripe/amount.html`,
  `mvp_payments/templates/cotton/drf_stripe/plan.html`,
  `mvp_payments/templates/cotton/drf_stripe/subscription.html` — the three components. `amount`
  renders a `Money`; `plan` renders one priced item's name, amount, frequency and quantity;
  `subscription` renders one `CurrentSubscription` as a `<c-card>` with the status as a `<c-badge>`
  carrying its own text and the period through `<c-data_field>`. A frequency of `month_1` renders
  through `ngettext`; an unrecognised one renders as itself. Every string is translatable.
- **T013** `mvp_payments/templates/mvp_payments/drf_stripe/subscription.html` — the page: the
  heading already there, then a loop over `subscriptions` rendering one `<c-drf-stripe.subscription>`
  each.
- **T014** `tests/test_components/test_drf_stripe.py`,
  `tests/test_components/__init__.py` — each of the three components rendered on its own in a
  throwaway template, given its attributes, asserting its output. Add `tests/test_components/` to
  `[tool.forge.conformance] non-mirror-paths` in `pyproject.toml` if it is not already covered.

## Phase 2 — US-2: Managing it happens at the provider (P1) → #19

### Tests first

- **T015** `tests/test_views.py::TestBillingPortalEndpoint` — the context carries
  `billing_portal_endpoint` from `settings.MVP_PAYMENTS["DRF_STRIPE_BILLING_PORTAL"]`; it is `None`
  when the setting is absent; it is `None` for a signed-in person with no current subscription even
  when the setting is set. Red before T017.
- **T016** [P] `tests/test_components/test_drf_stripe.py::TestPortalLink` — given an endpoint, the
  component renders a control carrying that endpoint and a CSRF token as data, an accessible name,
  a note that it leads to the provider's site, and a failure message element that starts hidden;
  given no endpoint, it renders the statement that the provider manages the subscription and says
  the portal cannot be reached, with no control. Red before T018.

### Then the code

- **T017** `mvp_payments/views.py` — `billing_portal_endpoint` in the context, absent-by-default
  setting read at render time, suppressed when there is no current subscription.
- **T018** `mvp_payments/templates/cotton/drf_stripe/portal_link.html` — the control, its
  accessible name, its off-site note and its hidden failure message. No provider address is written
  here; the component knows only the backend's endpoint.
- **T019** `mvp_payments/static/mvp_payments/drf_stripe/billing_portal.js` — bind the control, post
  with the CSRF token, follow the `url` in a successful answer, reveal the failure message
  otherwise. No build step, no bundler, no external origin. It states what it needs and fails
  visibly, per Article XIII.
- **T020** `mvp_payments/templates/mvp_payments/drf_stripe/subscription.html`, `demo/` — place the
  control on the page beneath the subscriptions; have the demo load the static file and set the
  endpoint in `MVP_PAYMENTS`.

## Phase 3 — US-3: What the plan gets you in the app (P2) → #20

### Tests first

- **T021** `tests/test_namespaces/test_drf_stripe_records.py::TestPlanFeatures` — a plan carries the
  features recorded against its product; a feature with a description carries it; a feature without
  one falls back to its identifier; a product with no features carries an empty collection; a
  feature recorded against a different product never appears. Red before T023.
- **T022** [P] `tests/test_components/test_drf_stripe.py::TestFeatures` — the component lists what
  it is given, shows a description where there is one and the identifier where there is not, and
  renders nothing at all when given none. Red before T024.

### Then the code

- **T023** `mvp_payments/namespaces/drf_stripe_records.py` — whatever the tests above show is
  missing from the feature reading T009 put in place.
- **T024** `mvp_payments/templates/cotton/drf_stripe/features.html`, and `plan.html` extended to
  render it beneath the plan it belongs to. A plan with no features renders no heading and no empty
  list.

## Phase 4 — US-4: Nothing current to show (P2) → #21

### Tests first

- **T025** `tests/test_views.py::TestNoCurrentSubscription` — a signed-in person the backend records
  no current subscription for gets a page saying so; no plan name, amount, frequency, status, period
  or feature appears on it; no portal control appears; a person with no customer record at all
  reaches the same page rather than an error. Assert the absence of each region rather than the
  absence of a class name. Red before T027.
- **T026** [P] `tests/test_components/test_drf_stripe.py::TestNoSubscription` — the component
  renders its heading and message on its own, given nothing.

### Then the code

- **T027** `mvp_payments/templates/cotton/drf_stripe/no_subscription.html` and the page's
  `{% empty %}` branch. Delegates to `<c-page.list.empty>` for the shape, supplying its own icon,
  heading and message.

## Phase 5 — US-5: A project makes the page its own (P3) → #22

### Tests first

- **T028** `tests/test_views.py::TestTemplateOverride` — a project template supplied under the
  page's own name renders every documented context value, with no view, no context processor and no
  query of its own. Drive it through a settings module whose template directories put a project
  copy first, as the suite already does for its other override cases. Red before T030.
- **T029** [P] `tests/test_components/test_drf_stripe.py::TestStandalone` — every component this
  feature added renders correctly when placed in an unrelated template and given its attributes,
  including the ones already asserted in earlier stories, gathered here as the guarantee SC-006
  names.

### Then the code and the documentation

- **T030** `docs/subscription-page.md` — the context names the page supplies, the shape of each
  value, every component and its attributes, how to override the template, and the one setting the
  portal control needs. Written for someone who has never read this repository.
- **T031** `README.md`, `CHANGELOG.md` — link the new page from the README's namespace section, and
  record the new components, the new context and the new setting in the CHANGELOG. The drf-stripe
  namespace's documented endpoint list gains `customer-portal/` (Article XVII).

## Convergence (S5, not a story)

- Squash the branch's migrations — none expected, the package ships none; confirm
  `makemigrations --check` is clean anyway.
- `craft-simplify` over the feature diff.
- ADR verdicts for every decision recorded in `decisions.md`.
- Full verify and tamper-check over the whole diff.
