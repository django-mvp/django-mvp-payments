# ADR 0003 — What counts as a current subscription is the backend's answer, never ours

**Status:** accepted

## Decision

`SubscriptionReader` reads a person's current subscriptions through the Stripe app's own
`Subscription.objects.for_user(user).current()`: every subscription that has not finished, in
whatever state Stripe reports. This package's interface layer names no
subscription status anywhere, and holds no list of which statuses count as current.

## Why

The backend already draws that line and applies it everywhere else it answers a question about a
person. A page that drew its own line would disagree with the application around it: somebody
locked out of a paid feature would be reading a page telling them their subscription is fine, and
the two answers would come from the same installation.

The alternative was to filter subscriptions on the status set ourselves, which means writing that
set down a second time in the interface layer. A copy of the list goes stale silently when the
original moves, and the one place that decides who is subscribed should stay the one place.

Reading the app's answer also disposes of the several-subscriptions question without a rule of our
own. The app returns every current subscription and the page renders each one, which is simpler
than choosing between them and is the only answer that cannot quietly hide one.

The page reads `current()` and not `subscribed()`. A person whose payment has failed is not
subscribed, but they still have a subscription, and the page is where they find out and reach
Stripe's portal to put it right (Article XV: every state is representable).

## Revisit if

Stripe adds a terminal status beyond `canceled` and `incomplete_expired`.
