# ADR 0002 — URL names are grouped under one application namespace and carry their own

**Status:** accepted

## Decision

Every page this package routes is named under a single application namespace, `payments`, and every
name within it carries the namespace of the backend that declared it:
`payments:drf-stripe-subscription`. `Contribution.url_name()` and `Contribution.view_name()` build
both halves, and `mvp_payments/urls.py` takes its `app_name` from the same constant they do.

A project includes `mvp_payments.urls` once, at a prefix of its choosing, and every installed
backend's pages arrive under it.

## Why

Two namespaces must not be able to share a URL name, and the cheapest way to guarantee that is to
make it impossible rather than to check for it. A name built from the namespace cannot collide with
one built from a different namespace.

A Django URL namespace per backend was the obvious alternative and was rejected. A namespace named
after a backend can be claimed by the project itself — nothing stops it mounting that backend's own
URL configuration under the same name — and reverse resolution is then ambiguous between two live
instances. The failure is silent and belongs to the project rather than to this package, which is
the worst combination.

One application namespace also keeps the include line singular. A project adds one line, not one
per backend, which is the promise the package is built around.

## Revisit if

A project needs two instances of this package's URLs mounted at once, under different prefixes.
Nothing supports that today and nothing asks for it, but a single application namespace is exactly
what would make it ambiguous.
