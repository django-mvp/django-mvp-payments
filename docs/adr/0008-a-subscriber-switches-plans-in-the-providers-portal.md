# ADR 0008 — A subscriber switches plans in the provider's portal, not the pricing table

**Status:** accepted

## Decision

On the subscription page, "Switch plans" is shown only to a current subscriber. It posts to the
Stripe app's plan-switch view and follows the address it answers with, which is the provider's
plan-change screen. With exactly one current subscription the screen is for that subscription. With
several, the view opens the portal's home and the person picks. It is bound by the same static file
as the portal control. "Choose a plan", for somebody with no subscription, is a link to the plans
page.

## Why

The provider's pricing table is built for a first purchase. It cannot say which plan the reader is
on, and choosing a plan from it sends them to checkout, which creates a new subscription. Changing
the plan they already have is a different job, and the provider's own documentation sends existing
subscribers to the customer portal for it.

The portal's plan-change screen shows the current plan and the cost of the change, and it changes
the subscription the person already has. Opening it directly, rather than on the portal's front
page, keeps "Switch plans" meaning what it says. With several subscriptions there is no one to open
it on, and choosing one for the person would be a guess, so the portal's front page is the honest
answer.

The view belongs to the Stripe app because only the app may call Stripe (Article XI).

The plans page is a separate question, and a subscriber may use it: they can buy a further plan
([ADR 0012](0012-the-plans-page-is-open-to-everyone.md)).

## Revisit if

The provider's pricing table learns to change an existing subscription, at which point "Switch
plans" could return to the plans page.
