# ADR 0015 — A customer is made before the first checkout

**Status:** accepted. Amends [ADR 0013](0013-the-plans-are-drawn-from-a-cached-catalogue.md).

## Decision

Every checkout the Stripe app starts names the person's own Stripe customer. When a signed-in person
with no customer picks a plan, `Customer.make_for()` asks Stripe to make one, with their email
address when the account has one, and records it before the Checkout Session is created. The session
is then created with `customer`, never `customer_email`.

## Why

- **Checkout makes a new customer every time it is not given one.** Before this, a person with no
  recorded customer bought with `customer_email`, and each such checkout made a fresh Stripe
  customer. If the first purchase was never tied to them (the webhook failing, the tab closed before
  the return) and they bought again, the second customer held a live subscription that was charging
  them, and `Customer.from_checkout()` refused it because the person already had the first. The
  site never showed the subscription and nothing in the app could cancel it.
- **It is what Stripe recommends.** A customer made on the server and passed to every checkout is
  Stripe's documented way to keep one customer per person.
- **The record still comes from Stripe.** The row is written from the customer Stripe returns, so
  local records still change only from what Stripe reports.

## What it costs

- A person who picks a plan and leaves the checkout has a Stripe customer with nothing bought, here
  and in the Stripe dashboard.
- Starting a first checkout is two calls to Stripe instead of one.
- Two checkouts started at the same moment by one person can both make a customer. The first
  recorded is theirs, and the other stays on Stripe with nothing bought on it.

## Revisit if

Stripe's checkout gains a way to reuse a customer it made for the same person, or a project needs
customers in the dashboard to mean only people who paid.
