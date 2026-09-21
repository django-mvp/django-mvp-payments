# Progress — 001 Payment pages that appear when you install a backend

## 2026-09-21

- Specification merged to main as #8. Issue graph built: epic #6, stories #9 to #13.
- Planning: `research.md` read the extension points out of django-mvp 0.23.0 and the backend out of
  its published distribution, and corrected two things the repository believed — the backend carries
  no upper version pins, and the README's installation order disables the overview card.
- `plan.md`, `tasks.md` and the ledger written. 32 tasks across a foundational phase and five
  stories.

## 2026-09-21T14:53:52Z · Implementer US1 · T005–T009 (tests first)

Did: wrote the five test files/classes the story's mechanism answers to — `test_contributions.py`
(`TestContribution`, `TestRepeatedRegistration`), `test_urls.py`, `test_views.py`,
`test_namespaces/test_drf_stripe.py` — plus the shared fixtures they need in `conftest.py`
(`user`, `logged_in_client`, `account_center_menu`). Committed one task per commit before writing
any implementation.
Verified: each file/class observed red for the right reason — `ModuleNotFoundError` for the
not-yet-built module under test, or (T008) `NoReverseMatch` for the not-yet-mounted `payments`
namespace.
Next: implement T010–T017.
Watch: T006's and T009's rendering assertions and T007/T008's URL assertions cannot go green until
the whole mechanism (T010–T016) lands together — they are paired with their primary implementation
task in `tasks.md`, not each independently satisfiable by one file.

## 2026-09-21T14:53:52Z · Implementer US1 · T012 (PaymentPageView)

Did: `mvp_payments/views.py` — `PaymentPageView(LoginRequiredMixin, MVPTemplateView)`, one class
built per `Page` via `as_view(page=...)`. `get_page()` raises `ImproperlyConfigured` if `page` was
never set, mirroring `BaseTemplateNameMixin`'s own idiom in django-mvp, and gives mypy a narrowed,
non-Optional value to work from.
Verified: `poetry run python -c "import mvp_payments.views"` under `tests.settings` — imports
clean. Built before T010 (out of tasks.md's listed order) because `Contribution.url_patterns()`
needs a real view to construct routes from, and building it after left `Page` unresolvable to mypy
(`Returning Any from function declared to return "str | Promise"`) since `contributions.py` didn't
exist yet for the `TYPE_CHECKING` import to resolve against.
Next: T010.
Watch: none.

## 2026-09-21T14:53:52Z · Implementer US1 · T010 (Contribution and Page)

Did: `mvp_payments/contributions.py` — frozen dataclasses `Page` and `Contribution`, with
`is_available()`, `is_reachable()`, `url_patterns()` and `register()`. `MenuItem` imported from
`mvp.menus` rather than `flex_menu` directly — the latter tripped `deptry`'s DEP003 (transitive
dependency) since only `django` and `django-mvp` are declared; `mvp.menus` already re-exports it
and is part of the declared `django-mvp` dependency.
Verified: `poetry run pytest tests/test_contributions.py::TestContribution -q` — 4 passed.
Next: T011.
Watch: none.

## 2026-09-21T14:53:52Z · Implementer US1 · T011 (the drf-stripe namespace)

Did: `mvp_payments/namespaces/drf_stripe.py` (the `drf_stripe` contribution — subscription, plans,
billing) and `mvp_payments/namespaces/__init__.py` (`CONTRIBUTIONS` tuple and
`available_contributions()`). Icons `subscription`, `plan` and `payments` — the three names the
demo's `EASY_ICONS` already declares for this purpose.
Verified: `poetry run pytest tests/test_namespaces/test_drf_stripe.py -v` — 3 of 4 passed; the
rendering assertion still red pending T015/T016 (registration and URL mounting), as expected.
Next: T013.
Watch: none.

## 2026-09-21T14:53:52Z · Implementer US1 · T013 (mvp_payments/urls.py)

Did: `app_name = "payments"`; `urlpatterns` collected from `available_contributions()`.
Verified: `poetry run python -c "..."` inspecting `mvp_payments.urls.urlpatterns` directly — three
routes, correctly named. `poetry run pytest tests/test_urls.py -q` — still 3 failed (payments
namespace not yet reachable via any mounted URLconf, pending T016), 1 passed (the
does-not-reverse case), as expected.
Next: T014.
Watch: none.

## 2026-09-21T14:53:52Z · Implementer US1 · T014 (page templates)

Did: `mvp_payments/templates/mvp_payments/drf_stripe/{subscription,plans,billing}.html` — each
extends `mvp/account/base.html` and fills `account.content` with `<c-page><c-page.title
:title="page.title" /></c-page>` alone.
Verified: no test scope of its own (T008 owns the rendering assertion); confirmed by file review
against `mvp/account/overview.html`'s own pattern.
Next: T015.
Watch: none.

## 2026-09-21T14:53:52Z · Implementer US1 · T015 (ready())

Did: `MvpPaymentsConfig.ready()` calls `register()` on every available contribution.
Verified: `poetry run pytest tests/test_namespaces/test_drf_stripe.py -v` — same 3 passed / 1
failed as before T015, confirming registration runs but entries stay hidden until the URL
configuration is mounted (django-flex-menus drops an item whose URL will not reverse, D3),
pending T016.
Next: T016.
Watch: none.

## 2026-09-21T14:53:52Z · Implementer US1 · T016 (mount in the demo)

Did: `demo/urls.py` — `path("payments/", include("mvp_payments.urls"))`.
Verified: `poetry run pytest tests/test_contributions.py tests/test_urls.py tests/test_views.py
tests/test_namespaces/ -v` — 17 passed after fixing two of this story's own test expectations
(below) and adding a missing `db` fixture. `poetry run pytest -q` (full suite) — 34 passed, no
regression in `test_app.py`/`test_demo.py`.
Next: T017.
Watch: two test corrections landed in this commit, not a separate one, because they were only
discoverable by running the completed mechanism: `mvp/account/base.html` draws
`AccountCenterMenu` twice (a collapsed mobile dropdown and a persistent desktop card), so a
registered entry legitimately renders twice, not once — `TestRepeatedRegistration` and
`TestDrfStripeContribution` both expected 1 and were corrected to 2. And every request touches
`CurrentSiteMiddleware`, which queries the database regardless of which view handles it, so the
anonymous-redirect test needed the `db` fixture even though it never signs in.

## 2026-09-21T14:53:52Z · Implementer US1 · T017 (documentation)

Did: README — `mvp_payments` before `mvp` in `INSTALLED_APPS` (D4), and the "pages are
`TemplateView`s" claim corrected to match `CONSTITUTION.md`'s amended Article XII. `CONTEXT.md` —
added *Contribution* to the glossary. `CHANGELOG.md` — recorded the URL configuration and the
drf-stripe namespace's three pages. `demo/templates/demo/home.html` — the same TemplateView
correction, and the "no components exist yet" notice updated to say the three pages are live in
the Account Center (flagged by the brief as about to stop being true).
Verified: `poetry run pytest -q` — 34 passed.
Next: story-level `forge verify`.
Watch: `AGENTS.md` still describes every view here as a `TemplateView` and the package as
Cotton-components-only, contradicting `CONSTITUTION.md`'s amended Article XII — out of this
story's named scope (T017 named README, CONTEXT.md and the changelog only), flagged in
`concerns` for the completion report.
