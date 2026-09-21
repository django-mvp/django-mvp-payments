# AGENTS.md — Agent Configuration for django-mvp-payments

<!-- Thin index only — bloat here = ignored instructions. Details live in the pointed-to files. -->

django-mvp-payments renders pricing, checkout and subscription interfaces as Cotton components.
Each payment backend gets its own component namespace and speaks that backend's own vocabulary:
`<c-drf-stripe.plan-grid>` is drf-stripe-subscription and nothing else. There is no neutral
component that renders through a swappable backend, and adding one is a constitutional change
rather than a feature. `CONTEXT.md` defines the terms; use them.

Presentation only, but not view-less. The package routes and renders the pages it ships; it holds
no state and decides nothing about money. No models, no migrations, no forms, no admin, no
serializers, and no module here imports `django.db` or a provider SDK. A view is a `TemplateView`
and stays one — a component gets its data from the backend's own HTTP endpoints, called from the
browser, and shows the answer someone else decided. `CONSTITUTION.md` Article XII is the rule and
`tests/test_app.py` is the gate.

Installing this package alone changes nothing a person can see. Installing it alongside a backend
makes that backend's pages appear in django-mvp's Account Center on their own, gated on
`apps.is_installed`, never on a settings flag (Article XIV). The one manual step is mounting this
package's URLs once, because Django gives an installed app no way to add routes to a project's
root URLconf.

No payment backend is a dependency of this package and none may become one. Nothing here imports
one, nothing here holds an API key, and no card details pass through it. `tests/test_app.py`
asserts the dependency list, because this is the property that keeps a project free to change
backends.

## Stack & commands

- **Stack:** Python 3.12+ / Django 5.2 and 6.0, Poetry-managed, built on django-mvp and Cotton
- **Install:** `poetry install`
- **Test:** `poetry run pytest`
- **Lint:** `poetry run pre-commit run --all-files` (ruff lint + format, mypy, deptry)
- **Type-check:** `poetry run mypy`
- **Build:** `poetry build`
- **Demo project:** `poetry run python manage.py runserver 0.0.0.0:8020`

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

`tests.yml` and `build.yml` deliberately carry no `paths:` filter on `pull_request`. A required
check that is filtered out never reports, and a check that never reports blocks the merge.

## Development workflow

Feature work follows a spec-driven process: spec → plan → tasks → implement → review → pull
request, with `specs/NNN-slug/` directories generated per feature. Project standards and the
quality bar live in `CONSTITUTION.md`.

`docs/brainstorm.md` holds the working notes the package was founded on: the prior-art survey, why
the first backend was chosen and what it constrains, and why there is no interface across
backends. Those are conclusions, not ratified decisions. Anything that hardens goes to
`CONSTITUTION.md` or an ADR.
