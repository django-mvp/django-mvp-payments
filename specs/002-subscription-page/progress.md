# Progress — 002 Show a person the subscription they are on

A narrative of the run, newest entry at the bottom. The ledger
(`feature-state.json`) is the machine record; this file is what a person reads to understand how
the feature got where it is.

## 2026-09-22 — S3 PLAN

Opened from the feature queue, which reported the feature ready with no dependencies outstanding
and no feature delivered in this repository since the specification landed, so there was nothing to
re-read the specification against.

The branch starts at `a5ac07fc3fdf0853787f41ee3eacff5101f2c182`, which is the merge of the
specification pull request (#17) and the current tip of the default branch. The verifier was green
on that commit before anything was written: lint, typecheck, the full suite, build and conformance
all passed.

Planning read the backend's models, its URL configuration and its billing-portal view, django-mvp's
component library, and this repository's standards document. What came out of it is in
`research.md`; the three readings that shaped the design were that the backend already exposes its
own definition of a current subscription as a property, that an amount arrives as an integer in a
currency's minor unit with no rendering attached, and that the portal endpoint answers a POST and
carries no route name, so it cannot be reversed and has to be supplied by the project.

## 2026-09-22 — S4 IMPLEMENT · US1 (T001–T003, foundational)

Did: `tests/factories.py` — one `DjangoModelFactory` per backend model the page reads, resolved by
string `Meta.model` through `apps.get_model`. `tests/conftest.py` — `stripe_user`, `current_subscription`
(one active subscription, one priced item) and `subscriber_client` fixtures wrapping them.
`demo/management/commands/seed_demo.py` — extended to seed `regular.user` with an active
subscription covering two priced items in different currencies on products that each carry a
feature, `staff.user` with a trialing one, `super.user` with none, and an unlisted fourth person's
subscription that must never appear on `regular.user`'s page.

Verified: `poetry run pytest tests/test_factories.py tests/test_conftest.py tests/test_demo.py` —
26 passed. `poetry run pre-commit run --all-files` clean on each commit.

Next: T004 — `money.py`.

Watch: none.

## 2026-09-22 — S4 IMPLEMENT · US1 (T004–T006, T008–T010 paired)

Did: `money.py` (`Money`, the currency-exponent table, `amount`, `__str__`) against its own new
`tests/test_money.py`; `namespaces/drf_stripe_records.py` (`PlanFeature`, `Plan`,
`CurrentSubscription`, `SubscriptionReader.for_user`, `frequency_display` through `ngettext`)
against `tests/test_namespaces/test_drf_stripe_records.py`; `Page.view` and `url_patterns()`
building from it against a new `TestPageView` class in `tests/test_contributions.py`. Each pair's
test was written and run first, confirmed failing for the right reason (`ModuleNotFoundError` /
`TypeError: unexpected keyword argument`), then the minimal implementation followed in the same
commit — see `decisions.md` D7 for why these three landed as one commit per pair rather than a
separate red and green commit each.

Verified: `poetry run pytest tests/test_money.py tests/test_namespaces/test_drf_stripe_records.py
tests/test_contributions.py` — 25 passed, including every pre-existing case. `mypy`, `ruff check`,
`ruff format --check` clean on each commit.

Next: T007, then T011 (the view itself needs all three pieces, so this one reverts to a red test
committed on its own).

Watch: none.

## 2026-09-22 — S4 IMPLEMENT · US1 (T007 test + T011 view/wiring)

Did: `tests/test_views.py::TestSubscriptionPage` — the view-level test covering plan name, amount,
frequency, status, period, two-item rendering with no third figure, an unrecognised status,
cross-user isolation and a fixed query count. Confirmed it fails for the right reason (the page
still only renders its heading). `views.py` — `SubscriptionPageView(PaymentPageView)` putting
`subscriptions` into the context via `SubscriptionReader.for_user`; `namespaces/drf_stripe.py` —
the subscription `Page` now names it (D4).

This intentionally stays red after T011 alone — the full rendered-output assertions also need
T012's components and T013's page loop, which is the next commit.

Verified: `poetry run pytest tests/test_views.py tests/test_namespaces/test_drf_stripe.py
tests/test_contributions.py` — 4 of `TestSubscriptionPage`'s 7 still red as expected (rendering
not wired yet), everything else green (27 passed). `mypy` clean after fixing an
`Any`-return warning on `get_context_data`.

Next: T012, T013.

Watch: the query-count test's first draft compared two sequential requests in one test and got a
false failure (6 vs 5 queries) from process-wide cache warmup (Site, ContentType) on the first
request — fixed by issuing one throwaway warmup request per client before capturing either.

## 2026-09-22 — S4 IMPLEMENT · US1 (T012 components + T013 page template)

Did: the three Cotton components — `amount.html` (a `Money`, or nothing without a currency),
`plan.html` (name, amount, frequency through `frequency_display`, quantity when above one),
`subscription.html` (a `<c-card>` with the status as a `<c-badge>` — a semantic variant for the
three statuses the reader can return, neutral otherwise — and the period through
`<c-data_field>`). The page template's `{% for %}` loop over `subscriptions`.

Hit `TemplateSyntaxError: 'blocktranslate' doesn't allow other block tags inside it` from
`{% blocktranslate count counter=plan.quantity %}` with no `{% plural %}` clause — Django requires
one whenever `count` is used. "Quantity: N" needs no plural form, so switched to
`{% blocktranslate with quantity=plan.quantity %}` instead of chasing a `count`/`plural` pair for
text that would say the same thing either way.

`tests/test_views.py::TestSubscriptionPage` went fully green here, and running the whole suite
surfaced one pre-existing failure: `tests/test_urls.py`'s parametrized assertion that every
declared page resolves to the generic `PaymentPageView`, written before `Page.view` existed. D4
(already reviewed) is exactly the decision this story changes for the subscription page — updated
the test to assert `SubscriptionPageView` for it and `PaymentPageView` for the other two; recorded
as D8 rather than silently changed.

Verified: `poetry run pytest tests/` — 87 passed, 0 failed. `mypy`, `ruff check`,
`ruff format --check` clean.

Next: T014.

Watch: none.

## 2026-09-22 — S4 IMPLEMENT · US1 (T014 component tests)

Did: `tests/test_components/test_drf_stripe.py` — each of the three components rendered standalone
through the `cotton_render` fixture (a bare request, no view, no login), given its attributes
directly as the dataclasses they are in production. Declared `tests/test_components/` under
`[tool.forge.conformance] non-mirror-paths` in `pyproject.toml` (was not yet covered).

All eight cases passed on the first run — expected, since they exercise the components T012 already
built from a different angle (standalone rendering) rather than driving new behaviour.

Verified: `poetry run pytest tests/` — 95 passed, 0 failed. `mypy`, `ruff check`,
`ruff format --check`, `deptry` clean.

Next: the story's completion report and the full `forge verify` run.

Watch: none.

## 2026-09-22 — S4 IMPLEMENT · US1 (verify: conformance failure on tests/test_conftest.py)

`forge verify --repo .` failed conformance: `tests/test_conftest.py` (added at T002 to prove the
fixtures) mirrors no source module — Article X's exception list covers `tests/factories.py` →
`tests/test_factories.py` by name, not a `conftest.py` test file, and the conformance tool's own
message says a cross-cutting test belongs as another `Test*` class in the module of its subject
rather than a file of its own. `tests/test_views.py::TestSubscriptionPage`, written for T007,
already exercises `subscriber_client` and `current_subscription` through real use (signed-in
request, period mutation, cross-user isolation), so the standalone file was redundant rather than
load-bearing. Removed it and pointed T002's ledger evidence at the tests that now cover it.

Verified: `poetry run pytest tests/` — 94 passed (one fewer than before, the coverage it added is
subsumed). `forge verify --repo .` re-run after — see the completion report for the full result.

## 2026-09-22 — S4 IMPLEMENT · US1 (resumed: docs gate red, and two plan corrections)

The run stopped between the US-1 completion report and the story's exit gate. Nothing was lost:
all fourteen tasks were committed, their tests green. Two things were not true yet.

`forge verify` was red on the docs step: six public names this story introduced — `Money`,
`SubscriptionReader`, `SubscriptionPageView`, `CurrentSubscription`, `Plan`, `PlanFeature` — that
no page documented. The plan put every documentation task in US-5 (T030, T031), which makes the
docs step red at every story boundary from here to the end of the feature. That is a planning
defect rather than a defect in the work: documentation ships with the code it describes, so each
story documents its own surface and US-5 extends the page rather than creating it.

Wrote `docs/subscription-page.md` covering what exists today: what counts as current and why the
backend decides it, the `subscriptions` context name, the shape of each value, the three
components, how to replace the template, and the two classes underneath. Linked it from the
README's namespace section, which also stopped claiming the subscription page shows nothing yet.
T030 and T031 now extend this page for the portal control, the feature list and the override
guarantee as those stories land.

Second correction: `_build_plan`, `_describe_frequency` and `_FREQUENCY_TRANSLATORS` carried
leading underscores, against the standing rule that nothing in this organisation marks a name
private that way. Both helpers also had a subject and belonged on it (Article XI). The frequency
table is now `Plan.FREQUENCY_TRANSLATORS` with the parsing inlined into `Plan.frequency_display`,
which is its only caller, and `_build_plan` is `SubscriptionReader.build_plan`. Behaviour is
unchanged.

Verified: `forge verify --repo . --base origin/main` — conformance, docs, lint, typecheck, test
and build all green. `poetry run pytest` — 92 passed. The committed tree before these changes also
collected 92, so the "94 passed" in the T014 entry and the completion report was miscounted rather
than a coverage loss.

Next: US-2.

Watch: none.

## 2026-09-22 — S4 IMPLEMENT · US2 (T015+T017 paired)

Did: `tests/test_views.py::TestBillingPortalEndpoint` — `billing_portal_endpoint` carries the
endpoint from `settings.MVP_PAYMENTS["DRF_STRIPE_BILLING_PORTAL"]` for a current subscriber, is
`None` when the setting is absent, and is `None` for a person with no current subscription even
when it is set. Confirmed it failed for the right reason (`KeyError` — the context carried no such
name). `views.py` — `SubscriptionPageView.get_context_data` reads it at render time and suppresses
it against the `subscriptions` tuple it already builds, never against a status. Landed together
per D7's precedent, so the tree stayed green between commits.

Verified: `poetry run pytest tests/test_views.py` — 16 passed. `mypy mvp_payments/views.py` clean.
`poetry run pre-commit run --files tests/test_views.py mvp_payments/views.py` clean (one
reformat by `ruff-format`, re-verified after).

Next: T016+T018.

Watch: none.

## 2026-09-22 — S4 IMPLEMENT · US2 (T016+T018 paired)

Did: `tests/test_components/test_drf_stripe.py::TestPortalLink` — given an endpoint, the component
carries it and a CSRF token as data, has an accessible control, an `aria-describedby` note that it
leads to the provider's site, and a failure message element that starts hidden; given none, it
states the provider manages the subscription and renders no control. Confirmed it failed for the
right reason (`TemplateDoesNotExist: cotton/drf_stripe/portal_link.html` — Cotton's fallback
lookup, not a missing file inside an existing namespace directory). `portal_link.html` — the
control and both branches, translated throughout.

Verified: `poetry run pytest tests/test_components/` — 10 passed. `poetry run pre-commit run
--files tests/test_components/test_drf_stripe.py mvp_payments/templates/cotton/drf_stripe/portal_link.html`
clean.

Next: T019.

Watch: none.

## 2026-09-22 — S4 IMPLEMENT · US2 (T019)

Did: `mvp_payments/static/mvp_payments/drf_stripe/billing_portal.js` — binds every portal-link
control on the page, posts to its `data-endpoint` with its `data-csrf-token` as the `X-CSRFToken`
header, follows `data.url` on success, reveals the control's own hidden failure message on any
failure (non-2xx response, malformed JSON, or a missing `url`). No build step, no bundler, no
external origin (Article XIII). Deliberately does not write the backend's own response into the
DOM — the failure message is static, translated text already in the template, and this file only
toggles its `hidden` attribute, consistent with Article XII's "no trust in what comes back".

No Python test: this file runs in the browser and this package cannot import it or call the
endpoint from Python (Article XII), so nothing here is unit-testable the way the rest of the
story is — recorded in the completion report's `concerns` rather than left unsaid.

Verified: `poetry run pre-commit run --files mvp_payments/static/mvp_payments/drf_stripe/billing_portal.js`
clean (no lint/format/type hooks apply to `.js`). `poetry run pytest tests/test_app.py` — 9 passed
(confirms the new static file changes nothing about the package's dependency or import
guarantees).

Next: T020.

Watch: none.

## 2026-09-22 — S4 IMPLEMENT · US2 (T020)

Did: `tests/test_views.py::TestSubscriptionPage::test_the_portal_control_sits_beneath_the_subscriptions`
— against the demo's real settings (no `override_settings`), the control appears after the
rendered subscriptions and the demo's page loads the static file. Confirmed it failed for the
right reason (`ValueError: substring not found` — the control wasn't on the page yet).
`mvp_payments/templates/mvp_payments/drf_stripe/subscription.html` — placed the control beneath
the loop. `demo/settings.py` — `MVP_PAYMENTS["DRF_STRIPE_BILLING_PORTAL"]` pointed at where the
demo mounts the backend's portal endpoint. `demo/templates/base.html` — loads
`billing_portal.js` at the `extra_js` block django-mvp's shell already exposes, the way the demo
already loads its other assets. `demo/urls.py` — mounted `drf_stripe.urls` under `api/stripe/`.

That last one surfaced a real defect on the first run: mounting it unconditionally broke
`tests/settings_without_backend.py`'s two tests (`RuntimeError: Model class
drf_stripe.models.StripeUser doesn't declare an explicit app_label` — importing `drf_stripe.urls`
imports its models, and a model with no explicit `app_label` needs its app installed to get one).
A real project's own URLconf would never unconditionally include a backend's routes it hadn't
installed either, so gated it on `apps.is_installed("drf_stripe")`, matching the property
`tests/settings_without_backend.py` already exists to prove.

Verified: `poetry run pytest tests/` — 98 passed, 0 failed (run in full given how much of this
task's diff sat in demo/ wiring rather than the package). `mypy demo/ mvp_payments/` clean.
`poetry run pre-commit run --files tests/test_views.py demo/urls.py demo/settings.py
demo/templates/base.html mvp_payments/templates/mvp_payments/drf_stripe/subscription.html` clean
(one reformat, re-verified after). Extended `docs/subscription-page.md` for
`billing_portal_endpoint`, the portal-link component, the `MVP_PAYMENTS` setting and loading the
static file.

Next: the story's completion report and the full verify run.

Watch: the "no endpoint" branch's fallback text ("the provider manages the subscription and the
portal cannot be reached") renders today for anyone with no current subscription too, since
`billing_portal_endpoint` is `None` for that case as well as for a genuinely unconfigured setting
— the component cannot tell the two apart from the prop alone. That wording is imprecise for
someone who never subscribed (US-4 territory, not this story's to fix: the page has no `{% empty
%}` branch yet, and building one is explicitly out of this story's scope). Flagged in the
completion report's `concerns` for US-4 to account for when it replaces this page's empty-list
behaviour.

## 2026-09-22 — S4 IMPLEMENT · US2 accepted, with one finding fixed

Verified the story independently rather than on its report: receipts green against the brief it
was dispatched with, `tamper-check` clean over `2fa817c..HEAD`, and `forge verify --repo . --base
origin/main` green on all six steps with 98 tests passing. The three declared deviations are all
sound — the paired commits follow US-1's D7, the conditional mount in `demo/urls.py` is what a
real project's URLconf does and the unconditional version genuinely broke the no-backend settings
module, and keeping the failure message as rendered translated text rather than writing the
backend's response into the DOM is the right call twice over.

One finding, which the story had flagged as a watch item and deferred to US-4: the page rendered
the portal component unconditionally, so a signed-in person with no subscription read that their
subscription is managed by the provider and that the portal cannot be reached. Both halves are
untrue for that reader. Deferring it was defensible — US-4 does replace what that page shows — but
it leaves a false statement on a live page in the meantime, and the fix is a one-line guard in a
template this story already owns. Fixed here rather than carried: `{% if subscriptions %}` around
the component, a page-level test that fails without it, and the documentation corrected to say
which reader the no-endpoint wording addresses. Recorded as D11.

The story's own component-level tests were left alone. They assert the component's behaviour given
an endpoint and given none, and both remain correct — the case they never covered was the page's,
which is where the new test sits.

Verified: `poetry run pytest` — 99 passed. `forge verify --repo . --base origin/main` — all six
steps green.

Next: US-3.

Watch: `billing_portal.js` has no automated test and cannot have one in this suite — the only
seam is a browser. It is covered by the walkthrough, not by pytest. The portal component's note
carries a fixed element id, so placing two of them on one page would duplicate it; the shipped
page places one, and US-5's standalone-rendering work should not introduce a second.

## 2026-09-22T05:12:09Z · Implementer US3 · T021

Did: wrote `TestPlanFeatures` in `tests/test_namespaces/test_drf_stripe_records.py` — a product's
features are carried onto its plan, a feature's own description is carried, one with none carries
its identifier, a product with none carries an empty tuple, and a feature recorded against a
different product never appears. All five passed on first run against `build_plan` as it stands.

Probed rather than trusted the pass, per `craft-tdd`'s "before you call a task done": zeroed
`Plan.features` in `build_plan` and reran — three of five failed for the right reason (the two that
stayed green assert an empty collection, which zeroing also produces). Restored, then mutated the
query to pull every product's `ProductFeature` rows instead of `price.product.linked_features` —
the different-product isolation test failed exactly as it should, asserting a leaked feature. File
restored to its original state before committing; the diff is test-only.

Verified: `poetry run pytest tests/test_namespaces/test_drf_stripe_records.py` — 16 passed.

Next: T022.

Watch: none.

## 2026-09-22T05:12:09Z · Implementer US3 · T022

Did: wrote `TestFeatures` in `tests/test_components/test_drf_stripe.py` — given features it lists
their descriptions, given one with no description it shows the identifier, given none it renders
no `<ul>` and no `<li>` at all.

Verified: `poetry run pytest tests/test_components/test_drf_stripe.py::TestFeatures` — red,
`TemplateDoesNotExist: cotton/drf_stripe/features/index.html`, the right reason (the component
doesn't exist yet). T024 adds it.

Next: T023.

Watch: none.

## 2026-09-22T05:12:09Z · Implementer US3 · T023

Did: nothing — T021's probes already show `build_plan` carries the right features, correctly
isolated per product, with the right fallback. No production change. This is the acceptance
criterion's own stated correct outcome, not a shortfall.

Verified: no new commands beyond T021's.

Next: T024.

Watch: none.

## 2026-09-22T05:30:00Z · Implementer US3 · T024

Did: added `cotton/drf_stripe/features.html` (T022's `TestFeatures` now green) and extended
`plan.html` to render it beneath the plan, with an outer wrapper carrying the per-plan border so
the divider separates whole plan+features blocks rather than sitting inside one plan (D12). Added
two `TestPlan` cases proving the integration and the no-features case. Extended
`docs/subscription-page.md`: the component to the components table and list, its row in `Plan`'s
attribute table already existed, and a new note on how drf-stripe-subscription records features
against a product (space-delimited metadata key) since a reader would need it and nothing
documented it yet. Recorded D12 (wrapper) and D13 (template-level fallback, independent of
`build_plan`'s own) in `decisions.md`.

Verified: `poetry run pytest tests/test_components/test_drf_stripe.py tests/test_views.py` — 33
passed. `TestPlan::test_its_features_render_beneath_it` observed red first
(`TemplateDoesNotExist`... then a missing-text assertion) before `features.html` and the `plan.html`
change turned it green.

Next: the story's completion report and the full verify run.

Watch: none.
