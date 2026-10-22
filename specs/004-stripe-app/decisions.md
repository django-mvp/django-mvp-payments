# Decisions — FS-004

Rationale too long for the spec's clarifications.

## D0a — A purchase is tied to the signed-in user, never matched by email

drf-stripe-subscription tied a Stripe customer to a user by email address alone. FS-003 worked
round that by passing the signed-in person's address to the pricing table, which still fails when
the person changes the address at checkout and attaches the purchase to nobody. Stripe carries a
reference of the project's choosing through checkout and returns it on the completed checkout.
Tying the customer to the user from that reference, or from a customer the app recorded itself,
leaves no case where a purchase lands on the wrong account. A customer that arrives with neither
is left unrecorded rather than guessed at, because a wrong match shows one person another
person's subscription.

**ADR:** none — a rule of this app's checkout handling, stated in the spec (FR-007)

## D0b — Every subscription is kept, not one per user

Stripe's pricing table starts a new subscription on every purchase, so a person who buys twice has
two. FS-003 hides the pricing table from a current subscriber, which makes this rare, but rare is
not never. Keeping only one would hide the second from staff, who are the people who need to see
it to refund it.

**ADR:** none — a data-model detail of this app, stated in the spec (FR-004)

## D0c — What counts as subscribed

Active and trialing count. A subscription cancelled at period end stays active on Stripe until the
period ends, so it counts until then without a rule of its own. Past due does not count: Stripe is
still retrying payment, and a project that wants a grace period reads the status itself. This is
the reading most write-ups of Stripe subscriptions settle on, and it keeps the check a single
query.

**ADR:** none — stated in the spec (FR-012) and documented for projects

## D0d — Sketch gate: none

The feature adds no page and changes none. The only new screen is the Django admin's own, which is
read-only and drawn by Django.

**ADR:** none — a gate decision, not a design one.

## D1 — The dev environment moves to stripe 16 in this feature

The `stripe-lite` extra needs stripe 16 and drf-stripe-subscription was held on stripe 7. Both
run in one environment once the demo stops mounting drf-stripe-subscription's URLconf, the only
route to its import of the removed `stripe.error` module (research, finding 5). So the backend
switch stays the separate piece of work the specification describes, and nothing here waits on
it.

**ADR:** none — a development-environment step that the next piece of work removes.

## D2 — One method writes every record

`Customer.sync()` is called by the webhook, the command, and after a checkout is tied. Nothing
else writes a subscription row, which is how Article XI's "records change only from the
provider" holds by construction rather than by review.

**ADR:** none — recorded in the constitution already (Article XI) and visible in the code.

## D3 — A second Stripe customer for the same user is logged, not recorded

See research, Decisions. Replacing the existing customer would orphan its subscriptions, and
keeping two would break the one-customer-per-user rule the admin and the subscribed check rely
on.

**ADR:** none — a local rule of this app, prevented at the source by the work that moves the pages.

## D4 — Design review applied

The design review returned two high findings, four medium and four low, all applied to
`plan.md` and `tasks.md`: a signed checkout reference (SEC-001), delete permission that still
lets the user admin cascade (ARCH-001), `default_auto_field` (ARCH-002), a `mypy_path` check
(ARCH-003), demo keys from the first task (SPEC-001), a row lock in `sync()` (ARCH-004), product
names fetched separately because the planned expansion is refused by Stripe (SPEC-002, confirmed
against the sandbox), `list_select_related` (ARCH-005), sequential stories (SPEC-003) and two
edge-case tests (SPEC-004). Deleting a user from the user admin removing their Stripe records is
the spec's own edge case, so ARCH-001 needs no change to the specification.

**ADR:** none — plan corrections, each visible in the code that implements it.
