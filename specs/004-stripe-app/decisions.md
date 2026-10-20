# Decisions — FS-004

Rationale too long for the spec's clarifications.

## A purchase is tied to the signed-in user, never matched by email

drf-stripe-subscription tied a Stripe customer to a user by email address alone. FS-003 worked
round that by passing the signed-in person's address to the pricing table, which still fails when
the person changes the address at checkout and attaches the purchase to nobody. Stripe carries a
reference of the project's choosing through checkout and returns it on the completed checkout.
Tying the customer to the user from that reference, or from a customer the app recorded itself,
leaves no case where a purchase lands on the wrong account. A customer that arrives with neither
is left unrecorded rather than guessed at, because a wrong match shows one person another
person's subscription.

## Every subscription is kept, not one per user

Stripe's pricing table starts a new subscription on every purchase, so a person who buys twice has
two. FS-003 hides the pricing table from a current subscriber, which makes this rare, but rare is
not never. Keeping only one would hide the second from staff, who are the people who need to see
it to refund it.

## What counts as subscribed

Active and trialing count. A subscription cancelled at period end stays active on Stripe until the
period ends, so it counts until then without a rule of its own. Past due does not count: Stripe is
still retrying payment, and a project that wants a grace period reads the status itself. This is
the reading most write-ups of Stripe subscriptions settle on, and it keeps the check a single
query.

## Sketch gate: none

The feature adds no page and changes none. The only new screen is the Django admin's own, which is
read-only and drawn by Django.
