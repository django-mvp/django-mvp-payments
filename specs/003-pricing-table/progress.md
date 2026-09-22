# Progress — 003 Offer plans through the provider's own pricing table

## 2026-09-22 — S3 PLAN

Picked off the feature queue as the only runnable feature across every registered repository.
Nothing had been delivered in this repository since the specification landed, so there was no
spec-against-spec comparison to make.

Branch `feat/003-pricing-table` off `origin/main` at `a73cbb1`, in a worktree of its own with the
commit identity bound to the repository's bot. Baseline verified green before anything was written:
lint, typecheck, test, build and conformance all passed on `a73cbb1`.

Read before planning:

- `drf_stripe/stripe_api/customers.py` at version 1.2.2 — the installed backend matches a provider
  customer to an application user on `customer.email` alone, confirming the assumption FR-005 rests
  on.
- The provider's published guide to the embeddable pricing table — the element's attribute list,
  and the fact that an undefined custom element renders as nothing with no event to listen for.

Both readings are recorded in `research.md`. The second settled how FR-010 is detected: one check
for whether the custom element is defined, which covers both the library never loading and the
provider's origin being unreachable, and nothing timing-based.

Plan written: one component, one view beside the one it mirrors, one static file, five stories in
priority order with no foundational phase, because this feature reads no record and needs nothing
seeded before the first story.

The plan carries one thing the specification anticipated: two sentences in the constitution forbid
reading a publishable key from settings anywhere in this package, and the shipped Plans page cannot
work under that reading. Both are narrowed to the component in US-5, with the reasoning left in
`decisions.md` where it already is.

## 2026-09-22 · Implementer US1 · T001

Did: wrote `TestPricingTable` in `tests/test_components/test_drf_stripe.py`, rendering
`<c-drf-stripe.pricing-table>` through `cotton_render` and asserting the `stripe-pricing-table`
element, both attribute values, no `<script`, and no figure that could read as an amount.
Verified: `poetry run pytest tests/test_components/test_drf_stripe.py::TestPricingTable` — red,
`TemplateDoesNotExist`, the right reason (T005's template does not exist yet).
Next: T002–T004's tests. Watch: none.

## 2026-09-22 · Implementer US1 · T002+T003

Did: wrote `TestPlansPage` in `tests/test_views.py` — context and content-region assertions with
both settings supplied, the anonymous redirect, and `MVP_PAYMENTS` absent entirely (via the
`settings` fixture's `del`, since `override_settings` cannot remove an attribute). Added
`_content_region()`, built on `tests.markup.account_navigation_regions`, to narrow the element
assertion away from the navigation's own "Plans" label. Combined T002 and T003 into one commit
rather than two — both tasks landed in the same edit to the same new class before either was run,
a deviation from one-task-one-commit noted here rather than re-split after the fact.
Verified: `poetry run pytest tests/test_views.py::TestPlansPage` — red on the three tests reading
context keys `PlansPageView` does not add yet (`KeyError`), green already on the anonymous-redirect
and import-reload tests, which hold pre-existing guarantees this story does not change.
Later revised twice, after T009 and T010 landed — see those entries.
Next: T004. Watch: none.

## 2026-09-22 · Implementer US1 · T004

Did: added `TestNoProviderScript` to `tests/test_app.py`, scanning every `.html` under
`mvp_payments/templates/` for a `<script>` element with a host `src`. Sanity-checked the regex by
hand against a real host-referencing script, a protocol-relative one, and this package's own
`{% static %}` script tag, confirming it flags the first two and not the third.
Verified: `poetry run pytest tests/test_app.py::TestNoProviderScript` — passes today, by
construction (no offending template exists yet); the task exists to hold the guarantee before T005
adds the component, not to be red first.
Next: T005. Watch: none.

## 2026-09-22 · Implementer US1 · T005

Did: wrote `mvp_payments/templates/cotton/drf_stripe/pricing_table.html` — `<c-vars table_id
publishable_key customer_email />`, emitting `<stripe-pricing-table>` with `pricing-table-id` and
`publishable-key`. `customer_email` is declared and not read, per the brief. Header comment follows
`portal_link.html`'s shape.
Verified: `poetry run pytest tests/test_components/test_drf_stripe.py::TestPricingTable` — green.
`poetry run pytest tests/test_app.py::TestNoProviderScript` — still green.
Next: T006. Watch: none.

## 2026-09-22 · Implementer US1 · T006

Did: added `PlansPageView(PaymentPageView)` to `mvp_payments/views.py`, beside
`SubscriptionPageView`, reading `pricing_table_id` and `publishable_key` from
`getattr(settings, "MVP_PAYMENTS", {})` at render time, each defaulting to `None`.
Verified: `DJANGO_SETTINGS_MODULE=tests.settings poetry run python -c "import django;
django.setup(); import mvp_payments.views"` — imports cleanly. Not yet wired to a URL, so
`TestPlansPage` still red for the expected reason.
Next: T007. Watch: none.

## 2026-09-22 · Implementer US1 · T007

Did: named `PlansPageView` on the Plans `Page` in `mvp_payments/namespaces/drf_stripe.py`, updated
the module docstring (no longer says the plans page renders only its heading).
Verified: `poetry run pytest tests/test_views.py::TestPlansPage tests/test_views.py::TestPaymentPage
tests/test_namespaces/test_drf_stripe.py` — 13 passed, 1 failed (the content-region assertion,
expected until T008).
Concern surfaced here: `tests/test_urls.py::TestPaymentURLs::test_declared_page_name_reverses_to_its_view[drf-stripe-plans-PaymentPageView]`
is a pre-existing test outside this story's file scope, asserting `drf-stripe-plans` resolves to
exactly `PaymentPageView`. This task's own acceptance criterion requires the opposite. Not
modified, per the prohibition on touching a pre-existing test I did not author — see this report's
`concerns`.
Next: T008. Watch: the `test_urls.py` collision above, for Forge.

## 2026-09-22 · Implementer US1 · T008

Did: `mvp_payments/templates/mvp_payments/drf_stripe/plans.html` now renders
`<c-drf-stripe.pricing-table :table_id="pricing_table_id" :publishable_key="publishable_key" />`
inside `<c-page>`, unconditionally (the unavailable branch is US-4).
Verified: `poetry run pytest tests/test_views.py tests/test_app.py
tests/test_components/test_drf_stripe.py tests/test_namespaces/` — 82 passed.
Next: T009. Watch: none.

## 2026-09-22 · Implementer US1 · T009

Did: added `DRF_STRIPE_PRICING_TABLE_ID` and `DRF_STRIPE_PUBLISHABLE_KEY` to `demo/settings.py`'s
`MVP_PAYMENTS`, clearly-fake values, commented as the demonstration's own.
Verified: `poetry run pytest tests/` — this exposed that `tests/settings.py` inherits
`MVP_PAYMENTS` from `demo/settings.py` via `from demo.settings import *`, so the "absent entirely"
test in T002+T003 needed the `settings` fixture's `del` rather than relying on the ambient absence
that held before this task. Fixed there (see T002+T003's revised entry) rather than as a new task.
1 failed (the pre-existing `test_urls.py` collision, expected), 129 passed.
Next: T010. Watch: none.

## 2026-09-22 · Implementer US1 · T010

Did: added `{% block provider_library %}` nested inside `demo/templates/base.html`'s existing
`extra_js` block, loading `https://js.stripe.com/v3/pricing-table.js` and this package's own
(not-yet-existing) `pricing_table.js`, commented as the host project's decision and forbidden to
self-host. Nested inside `extra_js` rather than declared bare, because a block outside every block
the parent chain already renders would never appear in output — nesting is what lets a child
template empty just this block while `extra_js`'s sibling content (the portal-link script) still
renders.
This made `js.stripe.com` appear on every demo page, including the Plans page, which broke my own
`test_the_rendered_page_carries_no_script_element_for_the_provider` from T002+T003 — a test I
authored this session, not a pre-existing one. Removed it and recorded why in `decisions.md` D2:
SC-002's guarantee is already held exhaustively and permanently by T004's static template scan, and
a runtime assertion against the full assembled response cannot hold once the demo, standing in for
a host project, correctly loads the library site-wide.
Verified: `poetry run pytest tests/` — 1 failed (the pre-existing `test_urls.py` collision), 128
passed.
Next: T011. Watch: none.

## 2026-09-22 · Implementer US1 · T011

Did: wrote `docs/plans-page.md` — the component and its three attributes (two functional, one
declared for a later story), the two settings the page reads, the page's template in full, and the
statement that loading the provider's library is the project's own decision. Every example matches
what the branch actually ships.
Verified: read back against `pricing_table.html`, `plans.html` and `demo/settings.py` line by line;
every name and every template fragment shown matches the branch as committed.
Next: full verify (§3), then the completion report. Watch: the `test_urls.py` collision remains
open for Forge.

## 2026-09-22 · Implementer US2 · T012

Did: added four tests to `TestPricingTable` — a signed-in person with an address carries it as
`customer-email`; a signed-in person with no address carries no `customer-email` attribute at all;
an anonymous visitor carries none; and an explicit `customer_email` attribute wins over the
signed-in person's own address. `cotton_render_string` was needed rather than the existing
`cotton_render` fixture — `cotton_render` renders through `render_component`, whose
`RequestContext` always resolves `request` from its own fixed, anonymous `RequestFactory` request
via the `django.template.context_processors.request` processor, which overrides anything placed
under the `request` key in the initial context dict. `cotton_render_string` builds a plain
`Context` with no context processors, so the `request` key from an explicit `context={...}` is the
one the template actually sees, letting a test attach a real `.user` to it.
Verified: `poetry run pytest tests/test_components/test_drf_stripe.py::TestPricingTable -v` — 2
failed for the right reason (`customer-email` not asserted in output because the current template
does not read `customer_email` or `request.user` at all), 3 passed (the pre-existing test, and the
two cases the unread attribute already satisfies by omission).
Next: T013. Watch: none.

## 2026-09-22 · Implementer US2 · T013

Did: added one test to `TestPlansPage` — the page rendered for a signed-in person whose account
carries an address shows that address on the element, asserted through the page's content region
rather than the component in isolation.
Verified: `poetry run pytest tests/test_views.py::TestPlansPage -v` — 1 failed for the right reason
(`customer-email` absent from the rendered content because the component does not yet read it), 4
passed (the pre-existing tests, untouched).
Next: T014. Watch: none.

## 2026-09-22 · Implementer US2 · T014

Did: `pricing_table.html` now resolves `customer-email`: the `customer_email` attribute wins when
supplied; otherwise `request.user.email` is used when `request.user.is_authenticated` and that
person holds an address; otherwise the attribute is omitted from the element entirely, via an
`{% if %}/{% elif %}` pair around the attribute rather than always emitting it with a possibly
empty value. Extended the header comment with why the address is passed at all, per T014's brief.
Verified: `poetry run pytest tests/test_components/test_drf_stripe.py::TestPricingTable
tests/test_views.py::TestPlansPage -v` — 10 passed, including T012's four new tests and T013's one.
Next: T015. Watch: none.

## 2026-09-22 · Implementer US2 · T015

Did: `docs/plans-page.md` — corrected the `customer_email` row in the attribute table (it is now
read, not declared-and-unread), and added a "Where the address comes from" section: the backend's
email-only matching, that an attribute wins, that the signed-in person's address is the fallback,
and that absence is omission rather than an empty attribute.
Verified: read back against `pricing_table.html` as committed at T014; every claim and the example
markup match the branch.
Next: full verify (§3), then the completion report. Watch: none.

## 2026-09-22 · Implementer US3 · T016

Did: added one test to `TestPricingTable` —
`test_renders_completely_from_its_attributes_alone_for_an_anonymous_visitor` — the component
placed inside a template that has nothing to do with any page of this package, given only
`table_id` and `publishable_key`, for an anonymous visitor, wrapped in
`django_assert_num_queries(0)`.
Verified: `poetry run pytest tests/test_components/test_drf_stripe.py::TestPricingTable -v` — first
run failed with `RuntimeError: Database access not allowed`, not the design claim under test:
`django_assert_num_queries` calls `ensure_connection()` to set up its capture context even to
prove zero queries ran, which pytest-django refuses without a db-enabling fixture. Added `db` to
the test's parameters; the test then passed immediately, with no change to the component. That is
the honest answer to the brief's question: T016 was red once, for an environment reason, and never
red for the design reason it exists to test — the component already renders completely from its
attributes alone, per US-1. 6 passed.
Next: T017. Watch: none.

## 2026-09-22 · Implementer US3 · T017

Did: added two tests to `TestHomePage` in `tests/test_demo.py` — the provider's element present
with the demo's own `prctbl_not_a_real_table` / `pk_test_not_a_real_key` values, and a line of
copy naming it as the same component the Account Center's Plans page renders. `home_page` already
carries an anonymous `client`, so no new fixture was needed for the anonymous case (FR-009).
Verified: `poetry run pytest tests/test_demo.py::TestHomePage -v` — both new tests failed for the
right reason (the assertions look for markup `demo/home.html` does not carry yet), the rest of the
class's pre-existing tests untouched and passing.
Next: T018. Watch: none.

## 2026-09-22 · Implementer US3 · T018

Did: placed `<c-drf-stripe.pricing-table>` on `demo/home.html`, in a new `<c-section>` matching
the page's existing shape, with the demo's table id and publishable key given directly as literal
attribute strings rather than read from settings through a view or context processor — the same
way a project's own template would supply them, and the guarantee T016 exists to prove. The
accompanying `<c-text>` carries the line of copy the second T017 test looks for.
Verified: `poetry run pytest tests/test_demo.py -v` — 18 passed, all of `TestHomePage` including
both new tests, no regression elsewhere in the file. `poetry run djlint
demo/templates/demo/home.html --profile django` — 0 errors.
Next: full verify (§5), then the completion report. Watch: T016 was red once, for the
`django_assert_num_queries` fixture requirement, and passed on first run for the guarantee itself
— recorded plainly per the brief's instruction, not smoothed into a conventional red/green story.

## 2026-09-22 · Implementer US4 · T019

Did: three tests added to `TestPlansPage` in `tests/test_views.py` — no table id configured
(scenario 1), no publishable key configured (scenario 2), and `MVP_PAYMENTS` absent entirely with
the heading and account navigation asserted unchanged alongside the unavailable sentence
(scenario 4, extending the pre-existing absent-settings coverage from US-1 rather than rewriting
`test_renders_with_mvp_payments_absent_from_settings_entirely`).
Verified: `poetry run pytest tests/test_views.py::TestPlansPage -x` — the three new tests failed
for the right reason: `plans.html` still renders the element unconditionally, so
`"stripe-pricing-table" not in content` failed against markup that plainly contains it.
Next: T020. Watch: none.

## 2026-09-22 · Implementer US4 · T020

Did: `TestPlansUnavailable` added to `tests/test_components/test_drf_stripe.py`, one test —
`<c-drf-stripe.plans-unavailable>` renders given no attributes at all.
Verified: `poetry run pytest tests/test_components/test_drf_stripe.py::TestPlansUnavailable -v` —
failed for the right reason, `TemplateDoesNotExist: cotton/drf_stripe/plans_unavailable.html` —
the component does not exist yet.
Next: T021. Watch: none.

## 2026-09-22 · Implementer US4 · T021

Did: one test added to `TestPricingTable` —
`test_carries_a_hidden_could_not_be_loaded_message_and_its_marker` — asserting the exact
`hidden data-mvp-payments-pricing-table-unavailable` attribute pair and the translated message
text appear together in the component's output.
Verified: `poetry run pytest
tests/test_components/test_drf_stripe.py::TestPricingTable::test_carries_a_hidden_could_not_be_loaded_message_and_its_marker`
— failed for the right reason: the marker string was absent from rendered output, which carried
only the `<stripe-pricing-table>` element.
Next: T022. Watch: none.

## 2026-09-22 · Implementer US4 · T022

Did: `mvp_payments/templates/cotton/drf_stripe/plans_unavailable.html` — takes no props, follows
`no_subscription.html`'s shape (`{% translate ... as name %}` pair, `<c-page.list.empty>`), heading
"Plans not available", message "This project has not configured its plans yet.".
Verified: `poetry run pytest tests/test_components/test_drf_stripe.py::TestPlansUnavailable -v` —
1 passed, T020's test green on first run of the new file.
Next: T023. Watch: none.

## 2026-09-22 · Implementer US4 · T023

Did: `mvp_payments/templates/mvp_payments/drf_stripe/plans.html` now branches: the pricing table
component when both `pricing_table_id` and `publishable_key` are present,
`<c-drf-stripe.plans-unavailable />` otherwise.
Verified: `poetry run pytest tests/test_views.py::TestPlansPage -v` — 8 passed, all three of
T019's new tests green; `poetry run pytest tests/test_views.py -v` — 30 passed, no regression
elsewhere in the file (`TestPaymentPage`, `TestSubscriptionPage`, `TestTemplateOverride` and the
rest untouched).
Next: T024. Watch: none.

## 2026-09-22 · Implementer US4 · T024

Did: `mvp_payments/templates/cotton/drf_stripe/pricing_table.html` now emits a
`<p hidden data-mvp-payments-pricing-table-unavailable>` carrying the translated
could-not-be-loaded message, after the `<stripe-pricing-table>` element — the shape
`portal_link.html` already uses for its own failure message. Added `{% load i18n %}`, absent from
the file until now since it carried no translated string.
Verified: `poetry run pytest tests/test_components/test_drf_stripe.py::TestPricingTable -v` — 7
passed, T021's test green, the zero-query assertion in
`test_renders_completely_from_its_attributes_alone_for_an_anonymous_visitor` still holding with
the added static markup. `poetry run pytest tests/test_views.py::TestPlansPage
tests/test_app.py -v` — 18 passed, including `TestNoProviderScript`, which still finds no script
element with a host `src` anywhere.
Next: T025. Watch: none.

## 2026-09-22 · Implementer US4 · T025

Did: `mvp_payments/static/mvp_payments/drf_stripe/pricing_table.js` — after the page's `load`
event, reveals every `[data-mvp-payments-pricing-table-unavailable]` element when
`customElements.get("stripe-pricing-table")` is undefined. Header comment names the check and why
a timing-based alternative was rejected, per `research.md`'s "Rejected without further reading"
section. No build step, no bundler, `querySelectorAll` over its own marker — `billing_portal.js`'s
shape.
Verified: no automated test exercises browser JavaScript in this suite; read back against
`research.md` and `billing_portal.js` for shape, and against `pricing_table.html`'s marker name
for an exact string match. `demo/templates/base.html` (already committed, outside this story's
scope) already references this exact static path, so nothing else needed to change to wire it in.
Next: T026. Watch: see `decisions.md` D8 — `pricing_table.js` and the provider's own script share
one overridable block in `demo/templates/base.html`, which affects what the demo's `no_library`
route (T026) can actually demonstrate live.

## 2026-09-22 · Implementer US4 · T026

Did: two demonstration routes, `demo/views.py` and `demo/urls.py` — `PlansUnconfiguredView`
renders `demo/templates/demo/plans_unconfigured.html`, which extends the package's own
`mvp_payments/drf_stripe/plans.html` through ordinary template inheritance with neither
`pricing_table_id` nor `publishable_key` supplied; `NoLibraryView` renders
`demo/templates/demo/no_library.html`, extending `page_view.html` with `provider_library` emptied
and the component placed directly with literal attributes, matching `home.html`'s T018 precedent.
Both linked from a new "Before it is configured" section on `demo/home.html`. Nothing under
`mvp_payments/` references either route.
Verified: no pytest task pairs with T026 in `tasks.md`, so no new test was written for it — a
Django test-client smoke check instead (`demo.settings`, `manage.py migrate` then `Client().get`
against `/`, `/plans-unconfigured/`, `/no-library/`) confirmed all three return 200, the
unconfigured route's content carries "Plans not available" and no `stripe-pricing-table` element,
the no-library route's content carries the element and the hidden marker, and the home page links
to both new paths. `poetry run pytest tests/test_app.py tests/test_views.py -q` — 40 passed, no
regression. `poetry run ruff check demo/views.py demo/urls.py` and `ruff format --check` on the
same two files — clean.
Next: T027. Watch: the port-8020 demo server named in this story's brief as "already serving this
branch" is running a different worktree's checkout on branch `feat/account-center-navigation`, so
it could not be used to verify these routes live; recorded as a concern rather than restarted or
reassigned, which is outside this story's authority.

## 2026-09-22 · Implementer US4 · T027

Did: `docs/plans-page.md` — corrected "The shipped page renders the component with both values
unconditionally" (now false) to describe the branch T023 added; added a "Before it is configured"
section documenting the unavailable sentence; added a "When the library never arrives" section
documenting the hidden message and `pricing_table.js`'s job, with the static-asset `<script>` tag
a project would add.
Verified: read every claim back against the templates and script as committed through T025;
`poetry run pytest tests/test_app.py -q` — 10 passed, unaffected by a docs-only change.
Next: full verify (§5), then the completion report. Watch: none beyond what is already recorded
above.
