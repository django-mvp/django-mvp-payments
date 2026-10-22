# ADR 0003 — What counts as a current subscription is the backend's answer, never ours

**Status:** accepted

## Decision

`SubscriptionReader` reads a person's current subscriptions through the Stripe app's own
`Subscription.objects.for_user(user).subscribed()`. This package's interface layer names no
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
own. The backend returns every subscription that counts and the page renders each one, which is
simpler than choosing between them and is the only answer that cannot quietly hide one.

The accepted cost: a subscription the Stripe app does not count, such as one that is past due,
does not appear on the page, so a person in that state reads as having no current subscription.

## Revisit if

The Stripe app's definition of subscribed grows a state the page should name, such as a payment
that has failed and can still be put right.
