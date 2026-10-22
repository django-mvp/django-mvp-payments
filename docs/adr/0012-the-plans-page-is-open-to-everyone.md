# ADR 0012 — The plans page is open to everyone

**Status:** accepted. Replaces the rule in [ADR 0008](0008-a-subscriber-switches-plans-in-the-providers-portal.md)
that kept the pricing table from a current subscriber.

## Decision

Any visitor can open the plans page, signed in or not, in any subscription state. It renders the
provider's pricing table for every signed-in person, subscribed or not. Only the user subscriptions page, which shows a person their
own subscriptions, requires a signed-in person.

For a signed-in person the page passes the table their signed reference
([ADR 0011](0011-a-checkout-is-tied-to-its-user-by-a-signed-reference.md)) and, when they already
have a Stripe customer, a customer session created on the server, so a further purchase lands on
the customer they have. A visitor who is not signed in is asked to sign in, and is given no table.
The table's buttons go straight to the provider's checkout from inside its own frame, so a notice
beside it could not stop a purchase that would be tied to nobody.

## Why

The plans a project offers are not private, so there is no reason to withhold them from someone
who has not signed in or who already subscribes. A subscriber may want a second subscription, and
the user subscriptions page lists every one they hold.

Keeping a subscriber from the table was meant to stop a second purchase from creating a second
customer. The customer session does that directly, so the page no longer needs to hide the table.

## What it costs

- A visitor who is not signed in cannot see the plans until they sign in. Showing them the plans
  without a way to buy needs the plans drawn by this package rather than by the provider's table,
  which is issue #61.
- Creating a customer session is a Stripe call on every page view by a signed-in customer. When it
  fails the page logs it and shows the table without the session, so a purchase may then create a
  second customer. Both customers still belong to the same user through the reference.

## Revisit if

The plans are drawn by this package with a checkout that requires sign-in (#61), at which point
every visitor can be shown them.
