# ADR 0011 — A checkout is tied to its user by a signed reference

**Status:** accepted

## Decision

The Stripe app ties a completed checkout to a user only through the checkout's
`client_reference_id`, and only when that reference verifies. The reference is built by
`Customer.client_reference(user)`: the user's primary key and an HMAC-SHA256 of it under the
project's `SECRET_KEY` and the app's own salt, joined by an underscore. Any page that starts a
checkout for a signed-in user, the plans page included, passes that value as the pricing table's
`client-reference-id`. Email addresses are never used to match a purchase to a user.

## Why

- **Email matching loses purchases.** drf-stripe-subscription matched on email address, so a
  person who typed a different address at checkout paid for a subscription that was attached to
  nobody.
- **A bare id can be forged.** A pricing table's id and publishable key are public by design. If
  the reference were the user's primary key alone, anyone could embed the table on a page of
  their own, put someone else's id in it, and tie their purchase, and their card details in the
  billing portal, to that person's account.
- **The pricing table limits the characters.** It accepts only letters, digits, dashes and
  underscores, which rules out `django.core.signing`, whose separator is a colon. An HMAC in hex
  with an underscore separator fits.

## What it costs

- Rotating `SECRET_KEY` invalidates the references of checkouts that are still open at that
  moment, so those purchases are recorded against nobody. Checkouts are short-lived, so the
  window is narrow.
- A checkout started anywhere that does not pass the reference, such as a payment link created
  in Stripe's dashboard, is not tied to any user.

## Revisit if

A project needs purchases made outside its own pages, such as payment links or invoices sent
from the dashboard, to reach a user. That needs another way to identify the user, chosen
deliberately rather than by falling back to email.
