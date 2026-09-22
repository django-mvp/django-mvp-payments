# ADR 0006 — A contributed page declares the view that renders it

**Status:** accepted

## Decision

`Page` carries a `view` field defaulting to `PaymentPageView`, and the URL configuration builds each
route from it. A page needing context the generic view cannot supply names its own view there, as
the subscription page does with `SubscriptionPageView`.

## Why

Until this feature every contributed page was the same view with a different template, which was
right while the pages were empty. A page that shows something has to get that something from
somewhere.

The alternative was a second URL configuration for the pages that need their own view. That puts
one namespace's routes in two places and breaks the property the previous feature was built around:
a contribution declares everything it contributes, and one condition decides all of it. A reader
asking what a namespace contributes would have had to know to look in two places, and a namespace
could have been half-registered.

## Revisit if

A page needs more than a view to differ — its own URL pattern, or more than one route — at which
point `Page` is being asked to carry a URL configuration and should say so.
