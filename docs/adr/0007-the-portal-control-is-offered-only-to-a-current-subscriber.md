# ADR 0007 — The portal control is offered only to somebody with a current subscription

**Status:** accepted

## Decision

`SubscriptionPageView` supplies `billing_portal_endpoint` only when the reader has at least one
current subscription, and the page renders `<c-stripe.portal-link>` only inside the same
condition. Somebody with nothing current is offered no control, no disabled control and no link
with an explanation, and reads nothing about a subscription at all.

The billing-portal view backs that up. It answers 409 to a person with no Stripe customer and never
creates one, so a stale page or a direct post cannot make a customer appear at Stripe.

## Why

A person who has never subscribed has nothing on the other side of the link. Offering them a control
that can only fail, or one that opens an empty portal, tells them something false about their
account.

The guard sits at the page rather than inside the component for a second reason. The endpoint is
absent for two unrelated causes: a reader with nothing current, and a project that renders the
component with no endpoint at all. The component receives only the endpoint and cannot tell those
apart, so its no-endpoint wording — that the subscription is managed by the provider and the portal
cannot be reached right now — is true of the second and false of the first. The page holds the
subscriptions as well as the endpoint, so it is the only place that can tell them apart.

## Revisit if

The component is given enough to distinguish the two cases itself, at which point the guard belongs
inside it rather than at the call site.
