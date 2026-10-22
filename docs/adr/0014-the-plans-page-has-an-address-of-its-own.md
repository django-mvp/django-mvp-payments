# ADR 0014 — The plans page has an address of its own

**Status:** accepted

## Decision

The plans page is not part of the Account Center. It is routed by `mvp_payments.plans_urls`
(namespace `payments_plans`, name `stripe-plans`), which a project includes at the address it
chooses, as a second line beside the one that includes `mvp_payments.urls`:

```python
path("account/billing/", include("mvp_payments.urls")),
path("plans/", include("mvp_payments.plans_urls")),
```

The user subscriptions page links to it when it is mounted and offers no link when it is not.

## Why

The plans page is public: it is where a visitor decides whether to sign up. A public page does
not belong under an account address, and where it lives (`/plans/`, `/pricing/`) is a choice
about the project's own site. Django gives an installed app no way to add a route to a project's
root URLconf, so the address can only come from an include the project writes.

## Revisit if

The Account Center gains a way for a package to contribute a page outside its own prefix.
