# Decisions — 001 Pages that arrive on install

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without asking the
maintainer. The specification stands alone; this file records why it says what it says.

## Why the pages arrive empty

The alternative was to ship the arrival mechanism proved by a single page and let each later
feature add its own route and navigation entry alongside its content. That reading was put to the
maintainer at intake and not taken.

Routing a page and filling it are different kinds of work, and splitting them per feature would
mean every later feature re-deciding where its page lives, what its address is and where its entry
sits — five chances to answer the same question differently. Deciding the shape of the page set
once, here, is what makes the later features additive. The cost is a period during which three
pages render a heading and nothing else, and the release gate for this stage already states that
it is pre-viable with nothing published.

No placeholder copy goes on those pages. Text apologising for an empty page is text written to be
deleted, and it would be the only thing on the page that no later feature owns.

## Why the demo installs the real backend

The first reading put to the maintainer was that the backend could not be installed here at all —
that its pins would reach this repository's own environment, so a stand-in application carrying
the same label would have to simulate it. He rejected that, and the rejection was right on the
facts.

The backend's published metadata declares `Django>=3.0`, `pydantic>=1.8` and `stripe>=2.63` with
no upper bound on any of them. The pinning described in the working notes was never true of the
published distribution. It resolves cleanly here against current Django and pydantic 2.

One real incompatibility survives. The backend imports a name from its payment provider's library
that was removed at version 8, so anything importing that module raises on a current release. The
development group therefore holds that library below 8. This is a development dependency of this
repository and nothing else: the package declares no backend, so no project installing it inherits
the constraint, which is the entire point of the dependency rule.

A stand-in would also have been worse on the merits. The claim under test is that installing a
backend makes its pages appear, and a stand-in tests that installing *something named like* a
backend makes pages appear.

## Why a second namespace exists only in the test suite

User Story 5 is the one guarantee that cannot be demonstrated with the backends that exist, because
there is exactly one. The claim is about independence between two contributions, and independence
needs two contributions and nothing else — not two real payment libraries. A second namespace
defined in the test suite, contributing through the same mechanism, answers it completely.

This does not reopen the question above. The demo installs a real backend because the demo is what
a person looks at. The test suite defines a second namespace because the property under test is
structural.

## Why entries sit directly in the navigation

A parent entry grouping a backend's pages would need a label, and the only accurate label is the
name of a Python library. Nobody reading their own subscription page has any use for that word, and
inventing a friendlier one would put a name on the navigation that appears nowhere else.

Grouping only pays when two backends are installed at once, and that is already unsupported, for a
reason that has nothing to do with navigation: with two live backends, whose subscription a person
is looking at stops being answerable, and nothing in this package arbitrates it.

## Why views were allowed to grow beyond rendering a template

The project's standards document restricted every view here to one that hands a template to the
renderer, on the reasoning that anything more would make the package a participant in the
application rather than a supplier of markup. The maintainer lifted that restriction at intake.

The consequence is larger than the sentence it changes, and it is recorded here because later
features inherit it. A page may now read the backend's records on the server and render them,
rather than every value arriving in the browser from the backend's HTTP endpoints. That makes the
components server-rendered markup with a context, and it is why the domain glossary's description
of how components reach a backend changes with this feature.

What did not change: no models, no migrations, no secret keys, no field a card number could be
typed into, no call to a payment provider from the server, and no arithmetic that decides what a
person is charged. Those are the package's identity rather than a restriction on how a page is
built. The no-dependency rule survives too, because a page reaches a backend's records through the
application registry rather than by importing the backend.

## Why the working notes are deleted rather than corrected

The founding notes carry a section arguing that the package ships no Python beyond an application
configuration, which the standards document and the README already contradicted before this
feature and which this feature contradicts outright. The maintainer's instruction at intake was
that the file is obsolete. Correcting one section of a document whose premise has moved leaves a
reader trusting the rest of it. The prior-art survey it also carries is preserved where it is
already stated — in the README's scope section and in the standards document's own articles.

---

# Decisions — planning

## D1 — A namespace declares one contribution, and one condition decides three surfaces

The entries, the pages and the card all have to appear and disappear together. Three independent
`apps.is_installed(...)` checks would do that today and drift later, and the drift that matters is
an entry pointing at a page that no longer exists.

One frozen dataclass per namespace holds what it contributes; `apps.ready()`, the URL configuration
and the template tag all read the same function for the available ones. The specification already
names *contribution* as a concept in its own glossary, so the class is the domain's vocabulary
rather than an invented layer. It is not a base class and nothing subclasses it.

**ADR:** to be decided at convergence.

## D2 — URL names are grouped under one application namespace, `payments`

FR-010 requires that two namespaces cannot share a URL name. Names are grouped under `app_name =
"payments"` and each carries its own namespace slug — `payments:drf-stripe-subscription` — so
collision is impossible by construction rather than by convention.

A Django URL namespace per backend was rejected: a namespace named after the backend's application
label can be claimed by a project mounting the backend's own URL configuration under that name, and
then `reverse` is ambiguous between two live instances.

**ADR:** to be decided at convergence.

## D3 — The card needs the same unreachability guard as the entry

django-flex-menus already hides a menu leaf whose URL will not reverse, which satisfies FR-009 for
the navigation with no code. The card is not covered by it: a card rendering a link through
`{% url %}` raises `NoReverseMatch` and takes the whole Account Center down with it, which is worse
than the dead link the requirement was written to prevent.

The availability check therefore has a second half — the namespace's pages reverse — and it lives
on `Contribution` beside `is_available()` so both surfaces read one answer.

**ADR:** to be decided at convergence.

## D4 — `mvp_payments` must precede `mvp` in a project's installed applications

Django's application template loader takes the first match for a template name in
`INSTALLED_APPS` order, and `{% extends %}` to the same name picks up the next one. The card
therefore only works when this package is listed above django-mvp.

The README currently instructs the opposite, which would leave a project with navigation entries
and no card and nothing to explain why. It is corrected on this branch, and the requirement is
documented as a requirement rather than a suggestion.

**ADR:** to be decided at convergence.

## D5 — Registration is idempotent by entry name

`AccountCenterMenu` is a module-level tree that outlives a development server's autoreload, and
`ready()` runs again on each reload. Without a guard the navigation accumulates duplicate entries,
which is invisible in a test suite that builds the tree once and obvious to anyone using the demo.

`register()` skips an entry whose name is already on the menu, and a test asserts that registering
twice renders the navigation once.

**ADR:** to be decided at convergence.

## D6 — Design review outcome

One reviewer, three lenses, one round. Two findings, neither of them blocking, and both applied
because both were cheap and correct.

**SPC-001 (medium, verified) — the task graph made a later story edit an earlier story's files.**
The card's unreachability guard sat in US-4 and would have had to reopen the class US-1 writes and
the template tag US-3 writes. Applied by moving the guard into the class where it belongs, in
US-1's own task, and by having US-3's tag ask for it from the start. US-4 is now the test that
makes it a guarantee and adds no code. The independence claim in `tasks.md` was also overstated and
now says what is true: stories run one at a time, in order, and no story edits a file an earlier
story created.

**SPC-002 (low, likely) — the unmounted-URLs state had no fixture named.** Every other test-support
file in the plan was named explicitly and this one was not. Applied by naming it.

Both halves of availability now live on `Contribution` for one reason worth recording: `ready()`
and the URL configuration may not reverse a URL, so the registry question and the reachability
question cannot be the same method. They are two methods with one home.

The reviewer spot-checked the research premises against the resolved packages and found no
discrepancy. It raised nothing under the security or architecture lenses.

**ADR:** to be decided at convergence.

## D7 — US-1 implementation notes

**Decision:** `mvp_payments/views.py` (T012) was built before `mvp_payments/contributions.py`
(T010), out of `tasks.md`'s listed order.
**Why:** `Contribution.url_patterns()` needs a real view callable to build routes from, so
`contributions.py` imports `PaymentPageView` at module level. Built in numeric order, `views.py`'s
`TYPE_CHECKING` import of `Page` (for `PaymentPageView.get_page() -> Page`) had nothing to resolve
against yet, and mypy correctly flagged the return type as `Any`. Building the view first, with no
dependency back on `contributions.py` at runtime, lets both files type-check cleanly at every
commit.
**Revisit if:** a future story needs to build a view before its contribution exists for a different
reason — the same reordering applies.

**Decision:** `mvp_payments/contributions.py` imports `MenuItem` from `mvp.menus`, not `flex_menu`
directly.
**Why:** `deptry` flags `flex_menu` as DEP003 (used but not declared — it's a transitive dependency
of `django-mvp`) the moment it's imported directly, and this package's dependency list must stay
exactly `django` and `django-mvp`. `mvp.menus` already re-exports `MenuItem` (it's how django-mvp's
own docstring teaches a consuming project to extend `AppMenu`), so importing from there satisfies
both the lint gate and the no-added-dependency rule without a workaround.
**Revisit if:** a future module here needs another `flex_menu` symbol `mvp.menus` doesn't
re-export — check whether `mvp.menus` or another `mvp` module already re-exports it before adding a
direct `flex_menu` import.

**Decision:** `PaymentPageView.page` is typed `Page | None = None`, with a `get_page()` method that
raises `ImproperlyConfigured` if it's still `None`, rather than asserting or leaving it unguarded.
**Why:** mirrors `BaseTemplateNameMixin.base_template_name`'s own idiom in django-mvp (a required
attribute set through `as_view(...)`, documented to raise `ImproperlyConfigured` at render time if
a subclass forgets it) rather than inventing a different pattern. A bare `assert` was rejected: `S101`
is a selected ruff rule for `mvp_payments/` (only relaxed for `tests/` and `demo/`), so it would
have failed lint.
**Revisit if:** a second required-attribute-via-`as_view` case appears here — factor the guard into
a shared mixin rather than duplicating the raise a third time.

**Decision:** `TestRepeatedRegistration` and `TestDrfStripeContribution` assert a registered entry's
`<span>{label}</span>` appears **twice** in the rendered Account Center page, not once.
**Why:** `mvp/account/base.html` (django-mvp, not this package) draws `AccountCenterMenu` at two
sites unconditionally — a collapsed mobile dropdown and a persistent desktop card — so every entry
legitimately renders twice regardless of viewport. This only became visible running the completed
mechanism end to end (T016); the tests were written expecting 1 and corrected once the real render
was observed.
**Revisit if:** `mvp/account/base.html` changes to draw the menu once, or conditionally.

## D8 — The documentation gate caught a page nobody had written

US-1 updated the README, the glossary and the changelog, and the documentation check still came
back red on five new public names. A changelog entry is not documentation and neither is a
docstring, which is exactly what the gate is there to say.

`docs/namespaces.md` was written at acceptance rather than re-dispatched for: it is one page of
prose about code that already existed and was already verified, and a fresh worker would have had
to read the whole story to write it. It documents what a namespace declares, the two questions a
contribution answers about itself, and the boundaries a namespace inherits.

**ADR:** to be decided at convergence.

## D9 — US-2's "backend absent" tests boot a fresh subprocess, not `override_settings`

**Decision:** `TestNothingWithoutABackend` (T019) opens the Account Center inside a subprocess
booted under `tests.settings_without_backend`, rather than using pytest-django's `settings` fixture
to override `INSTALLED_APPS` mid-test.
**Why:** confirmed by hand before writing the test — `mvp_payments/urls.py` builds `urlpatterns`
once, at first import, from `available_contributions()`; `MvpPaymentsConfig.ready()` registers
`AccountCenterMenu` entries once, at Django startup. Overriding `INSTALLED_APPS` afterwards
correctly flips `apps.is_installed("drf_stripe")` to `False` (Django's `setting_changed` signal
repopulates the app registry), but the already-built `urlpatterns` list and the already-registered
menu entries do not re-evaluate: `reverse("payments:drf-stripe-subscription")` kept succeeding
after the override in a manual check. A sibling package (`django-accounts-center`) uses
`override_settings` for exactly this shape of test, but only to render one component directly —
it never routes through an already-mounted URLconf, so it doesn't hit this. A process that never
had the backend in `INSTALLED_APPS` is the only way to observe what a project without it gets, so
`tests/settings_without_backend.py` (T018) exists to be a fresh process's settings module, and
`TestNothingWithoutABackend` boots one via `subprocess.run([sys.executable, "-c", ...])`.
**Revisit if:** a future story needs the same "as if never installed" guarantee for something that
does update per-request (there `settings`/`override_settings` would be simpler and should be
preferred) — the subprocess is specifically for surfaces built once at import/startup.

## D10 — Proving `{{ block.super }}` was kept also needs a fresh process, not `override_settings`

**Decision:** `TestAccountCenterOverview` (T023) opens the Account Center inside a subprocess
booted under a new `tests.settings_with_another_card`, which inserts a minimal fixture application
(`tests/other_app/`, shipping its own `mvp/account/overview.html` override) between `mvp_payments`
and `mvp` in `INSTALLED_APPS`.
**Why:** confirmed by hand before settling on this — `django.test.signals` resets the template
engine's app-directory cache on an `INSTALLED_APPS` change (unlike D9's URLconf/menu case), so
`override_settings(INSTALLED_APPS=...)` mid-test does make `get_app_template_dirs()` see the
fixture app, and `django.template.loader.get_template("mvp/account/overview.html")` correctly
resolves to `mvp_payments`'s own copy first. But the rendered response still showed only the
fixture app's card, never this package's — `django_cotton`'s own template resolution (used to
render `<c-card>` inside `mvp_payments/card.html`) does not observe that same reset, so the tag's
own template lookups stayed stale mid-test. A fresh process sidesteps the whole question, the same
way D9's does, and stays consistent with the one mechanism this story already reuses.
**Revisit if:** django-cotton starts responding to `INSTALLED_APPS` overrides itself, or this
package drops its dependency on `<c-card>` for this template.

## D11 — The card's heading is the first page's label, not a new field on `Contribution`

**Decision:** the card's heading is `contribution.pages[0].label` — the first declared page's
existing translatable label — rather than a new attribute added to `Contribution`.
**Why:** the brief prohibits changing `mvp_payments/contributions.py`, and `Contribution` already
carries no separate "namespace title" concept — only `backend_app_label`, `namespace` (a routing
slug, not prose), `pages` and `card_template`. Every page's `label` is already required to be
translatable (Article VIII, FR-011); reusing it avoids introducing a second, uncoordinated piece of
translatable copy for the same namespace, and keeps the card's link and its heading pointing at the
same thing — the namespace's first page.
**Revisit if:** a namespace ever needs a card heading that differs from its first page's name —
that would be the point to add a dedicated field to `Contribution`, brief permitting.

## D12 — The card's `<h2>` skips `<c-card>`'s `title` prop

**Decision:** `mvp_payments/card.html` writes its own `<h2 class="card-title">{{ heading }}</h2>`
into `<c-card>`'s default slot, instead of passing `heading` through the `title` prop.
**Why:** `<c-card :title="...">` wraps its heading as `<span>{{ title }}</span>`, and the shipped
namespace's first page is titled "Subscription" — the exact text
`TestRepeatedRegistration.test_registering_twice_does_not_duplicate_entries` (T006, US-1) counts
occurrences of as `<span>Subscription</span>` to prove the navigation isn't duplicated. Using the
`title` prop made that pre-existing test see three matches instead of two once the card existed, a
coincidental text collision rather than a real duplication. That test predates this story and
records real intent, so scope stayed on this package's own template.
**Revisit if:** `<c-card>` changes its `title` prop's markup so it no longer collides, or the
navigation's own rendering changes what it counts.

## D13 — Two items held for the convergence pass

Both came out of story reports and neither belongs to a story that could fix it.

**The card writes its own heading markup.** `mvp_payments/templates/mvp_payments/card.html` renders
an `<h2 class="card-title">` rather than passing a title to the packaged card component, because
that component's markup collides with an assertion in the first story's tests that counts
occurrences of a label inside a `<span>`. The assertion is the thing that is too broad — it should
be scoped to the navigation it is actually about — and a story may not edit an earlier story's
tests. Hand-written markup carrying a literal class name where a packaged component exists is
exactly what this project's review standard rejects, so the assertion is tightened at convergence
and the card then uses the component.

**`AGENTS.md` still describes every view here as a template-rendering one** and the package as
Cotton components only. Article XII was amended in this feature's foundational phase and two
separate story reports have now flagged the contradiction. It was outside every story's named
scope, which is correct — it is repository-level documentation, not a story's surface.

**ADR:** to be decided at convergence.
