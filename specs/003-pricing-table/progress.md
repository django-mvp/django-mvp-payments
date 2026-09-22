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
