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

## 2026-09-21T17:15:00Z · Implementer US2 · T018 (`tests/settings_without_backend.py`)

Did: added the settings module, inheriting `tests.settings` and filtering `drf_stripe` out of
`INSTALLED_APPS`.
Verified: `DJANGO_SETTINGS_MODULE=tests.settings_without_backend poetry run python -c "..."` —
`django.setup()` then `call_command('check')` prints "System check identified no issues", confirming
"Django starts cleanly". Also checked `apps.is_installed('drf_stripe')` is `False` and
`mvp_payments.urls.urlpatterns` is empty in that fresh process. Before settling on a settings module,
tried `override_settings(INSTALLED_APPS=...)` in-process and confirmed it does *not* work for this
story: `apps.is_installed` correctly flips, but `mvp_payments.urls.urlpatterns` was already built at
import time and `reverse("payments:drf-stripe-subscription")` kept succeeding after the override —
recorded as D9.
Next: T019.
Watch: the design consequence of D9 — anything reading `available_contributions()` at import time
(the URLconf) or once at startup (menu registration) can only be tested "as if absent" from a fresh
process, not from a settings override.

## 2026-09-21T17:20:00Z · Implementer US2 · T019 (`tests/test_app.py::TestNothingWithoutABackend`)

Did: added `TestNothingWithoutABackend`, which boots a subprocess under
`tests.settings_without_backend`, signs a person in, opens the Account Center, and asserts:
status 200, `aria-label="Account navigation"` still present (the page isn't broken), no
`<span>{label}</span>` for any of `drf_stripe`'s three page labels (covers both the nav entry and
where a future card would render its label — there's no card template yet, US-3's), and none of the
three page names reverse.
Verified: `poetry run pytest tests/test_app.py -v` — 8 passed (0.9-1.1s). Negative-test proof:
temporarily edited `tests/settings_without_backend.py` to *not* filter `drf_stripe` out (simulating
a leak), reran the standalone probe script directly — the three labels appeared (count 4 each, not
0) and all three page names reversed (`True`), confirming the assertions have teeth. Reverted before
committing; `git diff --stat` showed the settings file byte-identical to its committed T018 state
afterward.
Next: T020.
Watch: `ruff` flagged `S603` on the `subprocess.run` call — suppressed inline with `# noqa: S603` and
a comment, since both arguments (`sys.executable`, a module-level string constant) are fully
controlled, no untrusted input.

## 2026-09-21T17:25:00Z · Implementer US2 · T020 (import/dependency scan reach)

Did: added `test_the_import_scan_reaches_every_module_this_feature_added` to `TestPackagedApp`,
pinning that `test_no_module_reaches_a_database_or_a_provider`'s `rglob("*.py")` walk visits every
module this feature added — `apps.py`, `contributions.py`, `urls.py`, `views.py`,
`namespaces/__init__.py`, `namespaces/drf_stripe.py`. Did not touch
`test_no_payment_backend_is_a_dependency` (already exactly what SC-002/acceptance scenario 2 needs,
reads package metadata rather than scanning modules).
Verified: `poetry run pytest tests/test_app.py -v` — 8 passed. Negative-test proof: temporarily added
`import stripe  # LEAK-SIMULATION` to `mvp_payments/namespaces/drf_stripe.py`, reran
`test_no_module_reaches_a_database_or_a_provider` alone — it failed, naming that exact line as the
offender, confirming the pre-existing scan genuinely reaches `namespaces/`. Reverted; `git diff
--stat mvp_payments/namespaces/drf_stripe.py` showed no output (byte-identical).
Next: T021.
Watch: none.

## 2026-09-21T17:28:00Z · Implementer US2 · T021 (implementation — expectation was nothing)

Did: nothing. Every test T019 and T020 added passed against the existing implementation on first
run (after the negative-test proofs confirmed they weren't trivially green) — `Contribution`'s
`is_available()`/`is_reachable()` and `available_contributions()` (D1, D3) already route every
surface (`ready()`, `mvp_payments/urls.py`) through one place, and no surface was found asking
`apps.is_installed()` for itself. Committed an empty commit (`git commit --allow-empty`) to keep the
task-per-commit ledger, per the ritual.
Verified: `poetry run pytest -q` (full suite) — 36 passed (base 34 + T019's 1 + T020's 1), no
regression.
Next: story-level `forge verify`.
Watch: none.
