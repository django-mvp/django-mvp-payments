# AGENTS.md — Agent Configuration for django-mvp-payments

<!-- Thin index only — bloat here = ignored instructions. Details live in the pointed-to files. -->

django-mvp-payments renders pricing, checkout and subscription interfaces for projects built on
django-mvp, and keeps the records behind them for the providers it supports. Each payment backend
gets its own namespace and speaks that backend's own vocabulary. There is no neutral component or
view that renders through a swappable backend, and adding one is a constitutional change rather
than a feature. `CONTEXT.md` defines the terms; use them.

The package has two kinds of part, and `CONSTITUTION.md` Article XI sets the rules for each.

- **The interface**, `mvp_payments`: components, and the pages, views, URLs and menu entries that
  place them. No models, no migrations, no forms, no admin, no serializers, and no import of
  `django.db` or a provider SDK. A view may read what a provider app keeps. It may not hold state,
  compute what a person is charged or reach a provider. `tests/test_app.py` is the gate.
- **A provider app**, such as `mvp_payments.stripe`: the local copy of one provider's customers
  and subscriptions, its webhook endpoint, and the views that hand a reader to the provider's
  hosted pages and bring them back. The provider is the source of truth. Records change only
  from what the provider reports, a webhook is verified and then answered by fetching from the
  provider, and nothing here takes a payment, holds a card or decides what anyone is charged or
  may access.

Installing this package alone changes nothing a person can see. Adding a provider app to
`INSTALLED_APPS` makes its pages appear in django-mvp's Account Center, gated on
`apps.is_installed`, never on a settings flag (Article XIII). The one manual step is mounting this
package's URLs once, because Django gives an installed app no way to add routes to a project's
root URLconf.

No third-party payment backend is a dependency of this package and none may become one. A
provider's SDK is declared only in its provider app's extra, `stripe-lite` for the Stripe app,
and imported nowhere else (Article XII). Secret keys come from the host project's settings and
never reach a template, a context, a log or a fixture. No card details pass through any of it.

The Stripe app replaces drf-stripe-subscription ([ADR 0010](docs/adr/0010-the-package-ships-its-own-stripe-app.md)).
Until its pages move across, the `drf-stripe` namespace still reads drf-stripe-subscription's
records through the application registry.

## Stack & commands

- **Stack:** Python 3.12+ / Django 5.2, 6.0 and 6.1, uv-managed (hatchling build backend), built on django-mvp and Cotton
- **Install:** `uv sync`
- **Test:** `uv run pytest`
- **Lint:** `uv run pre-commit run --all-files` (ruff lint + format, mypy, deptry)
- **Type-check:** `uv run mypy`
- **Build:** `uv build`
- **Bump the version:** `uv version`. Never edit `pyproject.toml` alone, because `uv.lock`
  records this package's own version too
- **Demo project:** `uv run python manage.py runserver 0.0.0.0:8020`

Lint is the pre-commit run, not a bare `ruff check .`: the hook config excludes `docs/` and
migrations, and a raw invocation reports findings in paths the gate does not cover.

## Component layout

Components live at `mvp_payments/templates/cotton/<backend>/<component>.html`. Cotton maps a tag's
first segment onto that directory and hyphens onto underscores, so `<c-drf-stripe.plan-grid>`
resolves to `cotton/drf_stripe/plan_grid.html`.

The directory is named for the **backend**, not for this package — unlike most packages in this
organisation, which namespace by package name. That is deliberate: the namespace is how a template
author chooses a backend, so it has to read as the backend. It also means a second one is added by
creating a directory next to the first, touching nothing that already works.

The name is load-bearing and fails quietly. A component Cotton cannot resolve renders as empty
output rather than raising, so a renamed directory breaks every tag in the namespace without an
error anywhere. `tests/test_app.py` asserts the directory exists for that reason.

Where a component needs JavaScript of its own, it ships as a static file under
`mvp_payments/static/` and is included by the host project. A provider's own library is never
emitted, vendored or served from here.

## Releasing

Releases run through the shared release flow, never by hand and never by pushing a tag.

1. Dispatch **Prepare Release** with a bump level. It opens a pull request carrying the version
   bump and the CHANGELOG section.
2. Merging that pull request is the release decision. **Tag Release** then cuts the tag and the
   GitHub Release from the merge commit.
3. **Publish** uploads to PyPI through trusted publishing. PyPI's trusted publisher is bound to
   the `publish.yml` filename — renaming that file breaks publishing until the PyPI project
   settings are changed to match.

`pyproject.toml` holds the version and is the single source of truth for all three steps.

Nothing has been released. Two things are needed before the first release: a PyPI trusted publisher
for this project pointed at `publish.yml`, and a `RELEASE_TOKEN` that can write to this repository.

**Tag Release skips a version with no matching CHANGELOG section**, which is what keeps the seed
version from being cut as a release. Leave the scaffold version under `## [Unreleased]` until
Prepare Release promotes it — writing a `## [0.0.1]` heading by hand makes the next push to
`pyproject.toml` tag and release it.

## Agent skills

### Issue tracker

Issues tracked in GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary mapped 1:1 to canonical roles (needs-triage, needs-info, ready-for-agent,
ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — one `CONTEXT.md` at root and `docs/adr/` for architectural decisions.
See `docs/agents/domain.md`.

### CI checks

CI runs from the shared reusable workflows in `django-mvp/shared`, pinned at `v0.4.1`. Because
they are called rather than inlined, those status checks carry their caller job as a prefix.
The required checks are:

- `call-build / Code Quality`
- `call-build / Security Scan`
- `call-build / Build Package`
- `call-tests / Test Python 3.12, Django 5.2`
- `call-tests / Test Python 3.12, Django 6.0`
- `call-tests / Test Python 3.13, Django 5.2`
- `call-tests / Test Python 3.13, Django 6.0`
- `call-tests / Test Python 3.12, Django 6.1`
- `call-tests / Test Python 3.13, Django 6.1`

`tests.yml` and `build.yml` deliberately carry no `paths:` filter on `pull_request`. A required
check that is filtered out never reports, and a check that never reports blocks the merge.

## Development workflow

Feature work follows a spec-driven process: spec → plan → tasks → implement → review → pull
request, with `specs/NNN-slug/` directories generated per feature. Project standards and the
quality bar live in `CONSTITUTION.md`.
