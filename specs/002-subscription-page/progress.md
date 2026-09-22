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
