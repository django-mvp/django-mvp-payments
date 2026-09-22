# ADR 0003 — What counts as a current subscription is the backend's answer, never ours

**Status:** accepted

## Decision

`SubscriptionReader` reads a person's current subscriptions through the backend's own
`StripeUser.current_subscription_items` and groups the rows it returns by subscription. This
package names no subscription status anywhere, and holds no list of which statuses count as
current.

## Why

The backend already draws that line and applies it everywhere else it answers a question about a
person. A page that drew its own line would disagree with the application around it: somebody
locked out of a paid feature would be reading a page telling them their subscription is fine, and
the two answers would come from the same installation.

The alternative was to filter subscriptions on the status set ourselves, which means writing that
set down here. A copy of somebody else's list, in a package with no way to know the original has
changed, goes stale silently and on their release schedule rather than ours.

Reading the property also disposes of the several-subscriptions question without a rule of our
own. The backend returns what it returns and the page renders each one, which is simpler than
choosing between them and is the only answer that cannot quietly hide one.

The accepted cost: a current subscription carrying no priced items would not appear at all, since
the property is expressed in items rather than subscriptions. The backend records items from the
provider's own line items, so a subscription without them is not a state the provider produces.

## Revisit if

The backend gains a subscription-level equivalent of that property, or a provider starts producing
subscriptions with no line items.
