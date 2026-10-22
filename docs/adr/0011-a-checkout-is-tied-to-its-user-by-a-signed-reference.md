# ADR 0011 — A checkout is tied to its user by a signed reference

**Status:** accepted

## Decision

The Stripe app ties a completed checkout to a user only through the checkout's
`client_reference_id`, and only when that reference verifies. The reference is built by
`Customer.client_reference(user)`: the user's primary key and an HMAC-SHA256 of it under the
project's `SECRET_KEY` and the app's own salt, joined by an underscore. Every checkout the app starts
for a signed-in user, from the plans page included, carries that value as the Checkout Session's
`client_reference_id`. Email addresses are never used to match a purchase to a user.

## Why

- **Email matching loses purchases.** The first backend (ADR 0009) matched on email address, so a
  person who typed a different address at checkout paid for a subscription that was attached to
  nobody.
- **A bare id can be forged.** If the reference were the user's primary key alone, anyone able
  to start a checkout outside this app, with an embed or a payment link, could put someone else's
  id in it, and tie their purchase, and their card details in the
  billing portal, to that person's account.
- **Stripe limits the characters.** Its embeds accept only letters, digits, dashes and
  underscores, which rules out `django.core.signing`, whose separator is a colon. An HMAC in hex
  with an underscore separator fits.

## What it costs

- A reference verifies under `SECRET_KEY` or any key in `SECRET_KEY_FALLBACKS`, so rotating the
  key loses nothing as long as the old one stays in the fallbacks for a day, the longest a checkout
  stays open. Removing a key from the fallbacks sooner invalidates the references of checkouts
  still open under it, and those purchases are recorded against nobody.
- A checkout started anywhere that does not pass the reference, such as a payment link created
  in Stripe's dashboard, is not tied to any user.

## Revisit if

A project needs purchases made outside its own pages, such as payment links or invoices sent
from the dashboard, to reach a user. That needs another way to identify the user, chosen
deliberately rather than by falling back to email.
