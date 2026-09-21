# Research — 001 Pages that arrive on install

Everything below was read from the installed dependency or the published distribution, not from
memory. Versions are the ones this branch builds against.

## django-mvp 0.23.0 — the extension points this feature needs

All three exist in the released version. None of them is newer than the floor in `pyproject.toml`.

| Need | What 0.23.0 gives | Where |
|---|---|---|
| Navigation entries | `AccountCenterMenu`, a `flex_menu.Menu` with `append(child)` and `extend(children)` | `mvp/menus.py` |
| A card on the overview | `{% block account.cards %}` inside `mvp/account/overview.html` | `mvp/templates/mvp/account/` |
| A page in the area's layout | `{% block account.content %}` inside `mvp/account/base.html` | same |
| A view shape to follow | `AccountCenterView(LoginRequiredMixin, MVPTemplateView)` | `mvp/views/account.py` |
| Page heading and breadcrumbs | `PageMixin`'s `page_title`, `page_subtitle`, `breadcrumbs`, exposed to templates as `{{ page.* }}` | `mvp/views/base.py` |

The area's landing page is registered un-namespaced as `account-center`.

## An unreachable entry is already hidden

`FR-009` needs no mechanism of its own. `flex_menu.MenuItem.process()` resolves each item's URL and,
when `reverse()` raises `NoReverseMatch`, sets a leaf item's `visible` to `False` and returns
(`flex_menu/menu.py`, the `if not processed.url` branch). A project that has not mounted this
package's URL configuration therefore sees no entry rather than a dead link, and nothing raises.

The same branch keeps a container visible when it has visible children, which does not apply here
because every entry this feature adds is a leaf.

## Template override ordering, and a correction to the README

Django's application template loader walks `INSTALLED_APPS` in order and takes the first match for
a template name. `{% extends %}` to the same name skips the template doing the extending and picks
up the next one. So `mvp_payments` must come **before** `mvp` in `INSTALLED_APPS` for its copy of
`mvp/account/overview.html` to be found first and for `{{ block.super }}` to reach django-mvp's.

The demo project already has that order. The README's install instructions say the opposite — "Add
it to `INSTALLED_APPS`, after `mvp`" — which would silently disable the card. The README is
corrected on this branch.

## Rendering a card only for an installed backend

The overview is rendered by django-mvp's own view, so nothing this package writes can add context
to it. That leaves a template tag as the only way for the overridden block to render one card per
*installed* backend. Registered template tags are an explicit exception to the project's cohesion
article, so a tag module is not a structural deviation.

Rejected alternatives: a context processor, which runs on every request in the project for one
block on one page; and shipping a per-backend template whose presence is conditional, which is
impossible because template directories come from installed applications and this package is always
installed.

## URL naming

`drf_stripe`'s own URL configuration declares no `app_name` and names none of its patterns, so
nothing of ours can collide with it by accident. It could still collide by choice if a project
mounted that configuration under the namespace `drf_stripe`.

The names this package reverses are therefore grouped under one application namespace, `payments`,
with each name carrying its own namespace slug — `payments:drf-stripe-subscription`. One namespace
declaration, no nesting, and two backends cannot share a name by construction, which is what
FR-010 asks for.

## drf-stripe-subscription 1.2.2 — what installing it actually costs

Read from the published distribution, because the founding notes described pins that are not in it.

- Declared requirements are `Django>=3.0`, `djangorestframework>=3.0`, `pydantic>=1.8` and
  `stripe>=2.63`. There is no upper bound on any of them. Resolution against current Django and
  pydantic 2.13 succeeds.
- `drf_stripe/serializers.py` imports `stripe.error.StripeError`, which was removed in
  stripe-python 8. Anything importing that module raises on a current release, which includes
  mounting the backend's URL configuration. The development group therefore holds `stripe` below 8;
  resolution picks 7.14.0.
- No pydantic-1-only construct appears anywhere in the package — no `@validator`, no
  `@root_validator`, no `class Config`, no `parse_obj` — so pydantic 2 is not a second obstacle.
- Its settings object supplies defaults for every key it reads, so adding it to a project's
  installed applications needs no configuration to avoid an error at startup.
- Its models import `django.db` and `django.contrib.auth`, and nothing else reaches the payment
  provider's library, so installing the application is safe even with the import above unfixed.

None of this reaches a project that installs this package, because the package declares no backend.
It is a constraint on this repository's own development environment and on the demo.

## What this feature does not need to research

The pages this feature contributes render a heading and nothing else, so nothing here reads a
subscription, a price or a currency. The backend's data shapes are the concern of R2, R3 and R5.
