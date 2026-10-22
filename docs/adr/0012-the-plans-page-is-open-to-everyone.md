# ADR 0012 — The plans page is open to everyone

**Status:** accepted. Replaces the rule in [ADR 0008](0008-a-subscriber-switches-plans-in-the-providers-portal.md)
that kept the pricing table from a current subscriber.

## Decision

Any visitor can read the plans page, signed in or not, in any subscription state. It renders the
provider's pricing table for all of them. Only the subscription page, which shows a person their
own subscriptions, requires a signed-in person.

For a signed-in person the page passes the table their signed reference
([ADR 0011](0011-a-checkout-is-tied-to-its-user-by-a-signed-reference.md)) and, when they already
have a Stripe customer, a customer session created on the server, so a further purchase lands on
the customer they have. For a visitor who is not signed in the page passes neither and says, above
the table, to sign in before choosing a plan. A purchase made without signing in is tied to nobody,
and the package does not try to recover it.

## Why

The plans a project offers are not private, so there is no reason to withhold them from someone
who has not signed in or who already subscribes. A subscriber may want a second subscription, and
the subscription page lists every one they hold.

Keeping a subscriber from the table was meant to stop a second purchase from creating a second
customer. The customer session does that directly, so the page no longer needs to hide the table.

## What it costs

- A visitor who ignores the notice and buys pays for a subscription nobody can see. The notice is
  the whole remedy.
- Creating a customer session is a Stripe call on every page view by a signed-in customer. When it
  fails the page logs it and shows the table without the session, so a purchase may then create a
  second customer. Both customers still belong to the same user through the reference.

## Revisit if

Stripe's pricing table accepts an email address alongside a customer session, or lets a visitor
who is not signed in be recognised some other way.
