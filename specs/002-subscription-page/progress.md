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
