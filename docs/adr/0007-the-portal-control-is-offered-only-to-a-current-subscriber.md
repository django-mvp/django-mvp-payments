# ADR 0007 — The portal control is offered only to somebody with a current subscription

**Status:** accepted

## Decision

`SubscriptionPageView` supplies `billing_portal_endpoint` only when the reader has at least one
current subscription, and the page renders `<c-drf-stripe.portal-link>` only inside the same
condition. Somebody with nothing current is offered no control, no disabled control and no link
with an explanation, and reads nothing about a subscription at all.

## Why

The safety half comes first. The backend's portal endpoint calls `get_or_create_stripe_user`, which
creates the missing row and then **creates a new customer at the provider** before minting a
session for it. A person who had never subscribed would, by clicking, acquire a customer record at
Stripe. The specification reasons that such a person has "nothing on the other side of the link",
which is not what happens — the requirement it states is right and its reasoning is not, so the
correction lives here.

The second half is why the guard sits at the page rather than inside the component. The endpoint is
absent for two unrelated reasons: a project that never configured it, and a reader with nothing
current. The component receives only the endpoint and cannot tell those apart, so its no-endpoint
wording — that the subscription is managed by the provider and the portal cannot be reached right
now — is true of the first and false of the second in both halves. The page holds the subscriptions
as well as the endpoint, so it is the only place that can tell them apart.

## Revisit if

The backend gains a way to mint a portal session without creating a customer, or the component is
given enough to distinguish the two cases itself, at which point the guard belongs inside it rather
than at the call site.
