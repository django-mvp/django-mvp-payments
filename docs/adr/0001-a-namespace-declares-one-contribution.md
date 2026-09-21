# ADR 0001 — A namespace declares one contribution, and installation alone decides what appears

**Status:** accepted

## Decision

Everything one payment backend puts into the Account Center — its pages, its navigation entries and
its card — is declared as a single `Contribution` object in
`mvp_payments/namespaces/<backend>.py`, and added to `CONTRIBUTIONS` in that package's `__init__`.
Nothing else declares any part of it.

A contribution is made when `apps.is_installed(...)` is true for the backend it names, and never
otherwise. There is no setting, no flag and no registry a project populates.

That question has two halves, and they are separate methods because they cannot be asked at the
same moment:

- `is_available()` asks the application registry and nothing else. `ready()` and the URL
  configuration both call it, and neither may reverse a URL at the point it runs.
- `is_reachable()` asks a second question on top of that one: whether the namespace's pages
  reverse. Only something rendering a page may ask.

Every surface reads `available_contributions()` rather than asking the registry for itself.

## Why

The entries, the pages and the card have to appear and disappear together. Three independent
installation checks would do that on the day they were written and drift afterwards, and the drift
that matters renders a navigation entry pointing at a page that no longer exists.

The split into two questions is forced by Django's startup order rather than chosen. Registration
happens in `ready()`, before the URL configuration is loaded, so a check that reverses a URL cannot
run there. The card is the one surface that must ask the second question, because it renders a link:
an entry whose URL will not reverse is quietly dropped by django-flex-menus, but a card whose link
will not reverse raises while rendering and takes the whole overview down with it. That is worse
than the dead link the rule exists to prevent.

`Contribution` is not a base class and nothing subclasses it. It exists because three surfaces must
agree on one answer, and because the specification names the concept in its own glossary.

## Revisit if

A surface appears that must contribute without an installed application behind it — a namespace for
a provider with no Django package at all, say. The gate would then need something other than the
application registry to read, and the whole shape of this decision changes with it.
