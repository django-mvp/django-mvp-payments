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

## 2026-09-21T17:35:00Z · Implementer US3 · T022 (`tests/test_templatetags/test_mvp_payments.py::TestPaymentCards`)

Did: added the test class, calling the not-yet-existing `payment_cards()` tag directly — one test
monkeypatches `available_contributions` (as imported into the tag module) to return the real
`drf_stripe` contribution and asserts exactly one `href` to its first page plus its heading text;
the other monkeypatches it to return `()` and asserts the tag renders the empty string.
Verified: `poetry run pytest tests/test_templatetags/test_mvp_payments.py -v` — collection failed
with `ModuleNotFoundError: No module named 'mvp_payments.templatetags'`, the right reason (T024
hasn't built it yet).
Next: T023.
Watch: none.

## 2026-09-21T17:40:00Z · Implementer US3 · T023 (`tests/test_views.py::TestAccountCenterOverview`)

Did: added the test, plus a fixture application `tests/other_app/` (a bare template override of
`mvp/account/overview.html` that adds a `data-testid="other-app-card"` marker through
`{{ block.super }}`) to make the block.super half of the acceptance non-vacuous. First attempt used
`override_settings(INSTALLED_APPS=...)` mid-test with the fixture app inserted before `mvp`; this
resolved `mvp_payments`'s own overview.html correctly (confirmed via `get_template().origin` and
`response.templates`) but the card rendered by `<c-card>` inside it never reached the response —
`django_cotton`'s own template resolution does not reset on an `INSTALLED_APPS` override the way
Django's own template engine cache does (D10). Rebuilt on the same mechanism T018/T019 already use:
a dedicated `tests/settings_with_another_card.py` and a subprocess-booted probe.
Verified: `poetry run pytest tests/test_views.py::TestAccountCenterOverview -v` — failed with
`assert 0 == 1` on the card's `href` (right reason: T024/T025 don't exist yet). Found and fixed a
bug in my own `_account_center_cards_region` helper along the way (see below) before trusting this
result — its balanced-div counter started `depth` at 0 instead of 1, so it returned only the first
nested `<div>` (the fixture's own marker) rather than the whole `account-center-cards` region;
confirmed the fix by diffing the helper's output against a hand-inspected full-page dump.
Next: T024.
Watch: none.

## 2026-09-21T17:55:00Z · Implementer US3 · T024 (`mvp_payments/templatetags/mvp_payments.py`)

Did: `payment_cards()`, a `simple_tag` rendering `contribution.card_template` for every contribution
`available_contributions()` returns and `is_reachable()` confirms, joined and marked safe — asking
`Contribution` rather than re-deriving either check (D3). Each contribution's context carries its
first page's `label` as `heading` and a precomputed `payments:<namespace>-<slug>` view name for the
template's own `{% url %}` (the naming scheme T007/T013 already treat as public — hardcoded in
`tests/test_urls.py`).
Verified: committed on its own, still red — `card.html` doesn't exist yet, so
`tests/test_templatetags/test_mvp_payments.py` fails on `TemplateDoesNotExist` at this point,
expected per the phase split (T024/T025 land together, same as T010-T015). `ruff` flagged `S308` on
the bare `mark_safe(...)`; addressed with an inline `# noqa: S308` and a comment (each piece is
already-escaped `render_to_string` output, not raw formatting of untrusted input). Green confirmed
together with T025, below.
Next: T025.
Watch: none.

## 2026-09-21T18:05:00Z · Implementer US3 · T025 (overview override, `mvp_payments/card.html`)

Did: `mvp_payments/templates/mvp/account/overview.html` extends the same template name, keeps
`{{ block.super }}`, loads and calls `{% payment_cards %}`. `mvp_payments/templates/mvp_payments/card.html`
wraps `<c-card>` in an `<a href="{% url page_view_name %}">`.
Verified: `poetry run pytest tests/test_templatetags/ tests/test_views.py tests/test_app.py
tests/test_contributions.py -q` — first run: 19 passed, 1 failed —
`TestRepeatedRegistration.test_registering_twice_does_not_duplicate_entries` (T006, US-1, not mine
to edit) went from 2 to 3 matches of `<span>Subscription</span>`, because `<c-card :title="heading">`
renders its title inside exactly that markup and the shipped page's label is "Subscription" — a
coincidental collision with an unrelated count, not a real duplicate registration (D12). Fixed by
writing the card's own `<h2 class="card-title">{{ heading }}</h2>` into `<c-card>`'s default slot
instead of its `title` prop. Reran the same four files — 20 passed.
Negative-test proof (T022/T023's absence and block.super assertions): temporarily dropped
`{{ block.super }}` from the overview override and reran `TestAccountCenterOverview` — failed on
the missing `other-app-card` marker, confirming the test would have caught a dropped `block.super`;
reverted (`git diff --stat` showed no output, byte-identical).
Next: T023's carried-forward item — re-prove `TestNothingWithoutABackend`'s absence against the real
card markup.
Watch: none.

## 2026-09-21T18:15:00Z · Implementer US3 · T023 carried-forward (`tests/test_app.py::TestNothingWithoutABackend`)

Did: added `test_account_center_shows_no_card_from_the_absent_backend`, a new method on the
existing `TestNothingWithoutABackend` class (not editing its existing test), reusing its private
`_open_the_account_center_without_the_backend()` helper and asserting the card's real `href` markup
does not appear when the backend is absent.
Verified: `poetry run pytest tests/test_app.py::TestNothingWithoutABackend -v` — 2 passed.
Negative-test proof: temporarily hardcoded a literal `<a href="/payments/drf-stripe/subscription/">`
into the overview override (simulating a leak independent of whether the URL could even reverse) and
reran the new test alone — it failed, naming the missing `href` in its diff; reverted (`git diff
--stat` showed no output, byte-identical) and reran — passed again.
Next: T026.
Watch: none.

## 2026-09-21T18:20:00Z · Implementer US3 · T026 (documentation)

Did: `CHANGELOG.md` — recorded the card landing. `README.md` and `docs/namespaces.md` were already
true for the card and the `INSTALLED_APPS` order (both written ahead of this story, in T017/US-1):
README already states the order is "load-bearing, not a style choice" and already names "its own
card to the Account Center's overview" alongside the pages; `docs/namespaces.md` already documents
`card_template`. Confirmed by reading both in full rather than assuming T017's note was still
accurate.
Verified: read `README.md` and `docs/namespaces.md` in full; no gap against the acceptance criteria
found.
Next: story-level `forge verify`.
Watch: none.

## 2026-09-21T18:35:00Z · Implementer US4 · T027 (`tests/test_views.py::TestURLsNotMounted`)

Did: `tests/urls_without_payments.py` — `demo/urls.py`'s routes with the one line mounting
`mvp_payments.urls` removed, named exactly as `tasks.md` specifies. `TestURLsNotMounted` opens the
Account Center under it via `override_settings(ROOT_URLCONF="tests.urls_without_payments")` and
asserts status 200, the navigation still renders (`aria-label="Account navigation"`), none of
`drf_stripe`'s three page labels appear as a nav `<span>`, and the cards region has no `<a href`
and none of the three labels — plus that the request itself doesn't raise (the test client
re-raises a view exception rather than swallowing it into a 500, so a bare `assert status == 200`
already proves nothing raised).
Verified: `poetry run pytest tests/test_views.py::TestURLsNotMounted -v` — 1 passed, first try, no
production code touched.
Negative-test proof: temporarily added `path("payments/", include("mvp_payments.urls"))` back into
`tests/urls_without_payments.py` (marked `# LEAK-SIMULATION`) and reran the same test alone — failed
on `assert '<span>Subscription</span>' not in ...`, the right reason (the include being back is
exactly what the test exists to catch). Reverted; `cat` and `git status --short` confirmed the file
matched its committed state before the next commit.
Next: T028.
Watch: chose `override_settings(ROOT_URLCONF=...)` over a fresh subprocess, unlike D9/D10 — see D14
for why, confirmed by hand before writing the test rather than assumed from the prior stories'
pattern.

## 2026-09-21T18:40:00Z · Implementer US4 · T028 (implementation — expectation was nothing)

Did: nothing. T027 passed against the existing implementation on its first run (after the
negative-test proof confirmed it wasn't vacuously green) — `Contribution.is_reachable()` (T010) and
django-flex-menus' own unreachable-leaf handling already answer both halves of FR-009, and T027
found no gap in either. Committed an empty commit (`git commit --allow-empty`) to keep the
task-per-commit ledger, per the ritual (same as T021's precedent).
Verified: `poetry run pytest -q` (full suite) — 41 passed (base 40 + T027's 1), no regression.
Next: story-level `forge verify`.
Watch: none.

## 2026-09-21T19:00:00Z · Implementer US5 · T029 (`tests/second_namespace/`, `TestSecondNamespaceFixture`)

Did: `tests/second_namespace/__init__.py` (a minimal installed application, mirroring
`tests/other_app/`'s shape) and `tests/second_namespace/contribution.py` (a `Contribution`
declared against it, through the exact same public constructor every real namespace uses, reusing
the existing `mvp_payments/drf_stripe/subscription.html` template rather than adding a new one).
`TestSecondNamespaceFixture` in `tests/test_contributions.py` proves `is_available()` and
`register()` work on it with no special case anywhere in `mvp_payments/`.
Verified: `poetry run pytest tests/test_contributions.py -v` — first run: 8 passed, 1 failed —
`test_registers_through_the_same_mechanism_as_the_shipped_namespace` — `second_namespace.is_available()`
was `False` even inside `override_settings(INSTALLED_APPS=[..., "tests.second_namespace"])`. Root
cause: `Contribution.is_available()` calls `apps.is_installed(self.backend_app_label)`, and
Django's `is_installed()` matches an installed app's full dotted **name** (`AppConfig.name`), not
its short **label** — confirmed by reading `django.apps.registry.Apps.is_installed`'s own
docstring. `backend_app_label="drf_stripe"` works today only because that backend is installed at
the top level, where its name and label coincide; this fixture is nested under `tests.`, where
they do not. Fixed by setting `backend_app_label="tests.second_namespace"` (the app's full dotted
name) rather than touching `mvp_payments/contributions.py` — not a special case, just the value the
existing mechanism actually needs. Reran: 10 passed.
Next: T030.
Watch: `backend_app_label`'s docstring and `docs/namespaces.md` both call it a "label"; it is
actually consulted as the app's dotted name. Flagged as a concern, not fixed — out of this story's
scope (the shipped namespace is unaffected, and the field's own module is off limits per the
brief's prohibitions).

## 2026-09-21T19:15:00Z · Implementer US5 · T030 (`tests/test_contributions.py::TestNamespaceIndependence`)

Did: `tests/settings_with_second_namespace.py` (`tests.settings` plus `tests.second_namespace`
installed — a fresh-process settings module the same shape as D9/D10's, not an
`override_settings` mid-test, because `mvp_payments/urls.py` builds `urlpatterns` once at import
and `MvpPaymentsConfig.ready()` registers entries once at startup). `TestNamespaceIndependence`
boots one fresh process per side via a shared subprocess probe (`_NAMESPACE_INDEPENDENCE_PROBE`)
that adds the fixture to `CONTRIBUTIONS` for that process only (D1) and re-calls the same
`ready()` Django already called once (idempotent by entry name, D5) — never a settings override
mid-test, and never anything added to the shipped tuple. Three tests: the first namespace's
rendered navigation, card href and page addresses are identical alone and alongside the second;
neither namespace's declared name resolves to the other's page; no two declared contributions
share a URL name (this last one in-process, no subprocess needed — `url_patterns()` is a pure
function of the declared pages).
Verified: `poetry run pytest tests/test_contributions.py -v` — 10 passed, first try.
Negative-test proof: temporarily set the fixture's `namespace` to `"drf-stripe"` and its page
`slug` to `"subscription"`, colliding exactly with the shipped contribution's URL name and entry
name. Reran `TestNamespaceIndependence` and `TestSecondNamespaceFixture` — 3 of 5 failed:
`test_no_two_declared_contributions_share_a_url_name` (4 names, 3 unique),
`test_neither_namespaces_pages_resolve_to_the_others` (one reverse came back `None`), and
`test_registers_through_the_same_mechanism_as_the_shipped_namespace` (`register()` silently
skipped the collision — entry already existed under that name). `test_the_first_namespaces_...`
stayed green, which is itself informative: `register()`'s idempotent-by-name check absorbs a
colliding second contribution rather than corrupting the first. Reverted (`diff` against the
committed fixture was empty); reran — 10 passed again.
Full suite: `poetry run pytest -q` — 46 passed (base 41 + this story's 5), no regression.
Next: T031.
Watch: none.

## 2026-09-21T19:25:00Z · Implementer US5 · T031 (implementation — expectation was nothing)

Did: nothing. T029 and T030 passed against the existing mechanism — the URL naming scheme already
carries the namespace slug (D2), and `Contribution`'s methods are already generic per-instance
behaviour with no shipped-namespace special case. `git diff <base>..HEAD -- mvp_payments/` is
empty. Committed an empty commit to keep the task-per-commit ledger, per the ritual (same as
T028's precedent).
Verified: `poetry run pytest -q` — 46 passed, no regression; `git diff 4922dd2..HEAD -- mvp_payments/ | wc -l` — 0.
Next: T032.
Watch: none.

## 2026-09-21T19:30:00Z · Implementer US5 · T032 (documentation)

Did: `docs/namespaces.md` was already true — read in full, it already says "A second backend gets
a namespace beside it rather than underneath it, and the two share no markup and no data shape,"
nothing to change. `README.md`'s Namespaces section named the same intention but didn't yet say
the guarantee holds for namespaces already installed, so added one clause. `CHANGELOG.md` records
the test suite guarantee this story landed.
Verified: read `README.md` and `docs/namespaces.md` in full against T032's acceptance criterion.
Next: story-level `forge verify`.
Watch: none.
