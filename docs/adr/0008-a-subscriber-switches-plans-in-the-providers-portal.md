# ADR 0008 — A subscriber switches plans in the provider's portal, never the pricing table

**Status:** accepted

## Decision

The pricing table is for people with no current subscription. The Plans page renders it only for
them. Anybody with a current subscription sees `<c-drf-stripe.already-subscribed>` there instead,
linking to the subscription page.

On the subscription page, "Switch plans" is shown only to a current subscriber. It posts to an
endpoint the project names in `MVP_PAYMENTS["DRF_STRIPE_PLAN_SWITCH"]` and follows the address it
answers with, which is the provider's plan-change screen for that person's existing subscription.
It is bound by the same static file as the portal control. Without the setting a subscriber is
offered no switch control. "Choose a plan", for somebody with no subscription, stays a link to the
Plans page.

## Why

The provider's pricing table is built for a first purchase. It cannot say which plan the reader is
on, and choosing a plan from it sends them to checkout, which creates a new subscription. For
somebody already subscribed that is a second subscription beside the first, charged twice. Their
provider's own documentation sends existing subscribers to the customer portal to change plans.

The portal's plan-change screen shows the current plan and the cost of the change, and it changes
the subscription the person already has. Opening it directly, rather than on the portal's front
page, keeps "Switch plans" meaning what it says.

The endpoint belongs to the project for the same reason the portal endpoint does. This package may
not call a provider (Article XII), and the backend ships no endpoint for the plan-change screen.
Naming the endpoint in settings is the pattern ADR 0005 already set.

Suppressing the control without the setting, rather than falling back to the Plans page, follows
from the first point. The only fallback available is the one that does the wrong thing. The portal
control remains and reaches the same screen if the portal's own settings allow switching.

## Revisit if

The backend gains an endpoint for the plan-change screen, at which point the setting points there
and the project's own endpoint goes. Or the provider's pricing table learns to change an existing
subscription, at which point it can be shown to subscribers again.
