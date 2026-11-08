# ADR 0017 — The package records referrals, and the project rewards them

**Status:** accepted, not yet implemented

## Decision

- A person's referral link, and who came through it, are recorded by
  [pinax-referrals](https://github.com/pinax/pinax-referrals), installed through an extra of its
  own.
- The friend's discount is a Stripe promotion code, entered on Stripe's checkout.
- When a referred person first subscribes, the Stripe app tells the host project, naming the
  referrer and the new subscriber.
- What the referrer gets is the host project's to decide and to give. The package never writes to a
  customer's Stripe balance and never issues a credit or a code on anyone's behalf.

## Why

Article XI says a defect here can never move money. Crediting a referrer means writing to a
customer's balance, which is moving money, decided by this package rather than on Stripe's own
pages. Handing the moment to the host project keeps that boundary where it is, and leaves the
reward to the project that sets its prices.

pinax-referrals is established and maintained (Django 6.1), records referrals even for visitors who
have not signed up yet, and needs nothing from the rest of Pinax.

## Revisit if

Two or more projects reward referrers in the same way, which would make that one way worth building
here, and a change to Article XI along with it.
