# Decisions — 005 Show the plans we offer and let only signed-in users buy one

Rationale too long to sit in `spec.md`, and the ambiguities resolved while specifying it.

## The pricing table is removed, not kept beside the plans

Keeping Stripe's pricing table as a second way to show plans would leave two components, two sets
of settings and two documented routes to maintain, and the one being kept is the one that cannot
stop a signed-out visitor buying a plan tied to no account. The capability the pricing table gave
a project, plans on a landing page, is kept by making the new plans placeable (User Story 5). The
package has never been released, so removing the component, `STRIPE_PRICING_TABLE_ID` and the
plans page's use of `STRIPE_PUBLISHABLE_KEY` costs no project anything (Article XVI).

What this changes elsewhere in the same pull request, so that every document describes the plans
page as it now is:

- `specs/003-pricing-table/spec.md`, rewritten where the plans page no longer behaves as it says
- `CONSTITUTION.md` Article XI, which names the pricing table as one of the places a plan is chosen
- ADR 0010, which says products and prices are not copied because the plans page uses the pricing
  table, and a new ADR recording that the catalogue is cached rather than stored in models
- ADR 0012, whose "revisit if" names this feature
- `CONTEXT.md`, whose "Plans page" entry says the plans come through the pricing table
- `docs/reference/plans-page.md` and `docs/how-to/point-stripe-at-the-webhook.md`

## A plan is a price, shown under its product

Stripe has no plan record. Its product is what a price is for, and its price is what a person
buys. A product with a monthly and a yearly price is two things a person can buy, and each needs
its own way to buy it, so the spec offers every price. How prices of one product are grouped on
the page is design, left to the sketch.

## Which prices are on offer

Active, recurring, fixed-amount prices of active products. The package handles subscriptions only
(ADR 0010 keeps one-off payments out of scope). Metered and tiered prices have no single amount
to show, and showing a partial figure on a pricing page is the one defect that costs a reader real
money (Article XV). A project that needs them asks, and that is its own change.

## A visitor who signs in comes back to the page, not to checkout

Creating a Stripe checkout is a state-changing request and belongs to a submission the person
makes, protected against cross-site requests. Following the sign-in redirect is a plain link. Sending a newly
signed-in person straight into checkout would mean creating checkouts from a link, which anyone
could plant on another site. One more press, on a page that already shows the plan they picked,
is the cost.

## A subscriber's own plan leads to their subscriptions page

ADR 0012 lets a subscriber buy further plans, and that is kept. Buying the very price they already
hold is almost always a mistake, and it would leave them paying twice. Marking it and sending them
to the user subscriptions page, where the portal can change it, prevents that without taking any
other plan away from them.

## Promotion codes are accepted at checkout, taxes and trials are not configured

These were set in Stripe's dashboard on the pricing table. A checkout created by the Stripe app
gets only what the app asks for. Promotion codes are a single switch with no setup for a project
that has none, so they are accepted. Collecting tax needs Stripe Tax set up on the account, and a
trial is a pricing decision, so neither is turned on until a project asks.

## The catalogue lives in the cache, cleared by webhooks and by sync

From the intake issue. A webhook about a product or price is verified like every other (Article
XI) and then only clears the cache, so the next showing of the page fetches the catalogue from
Stripe. A webhook is a prompt, never the data. The expiry is the backstop for a missed webhook,
and the sync command clears the cache so a developer who has just edited prices need not wait for
either.

## Self-resolved ambiguities

None was left marked for clarification. The five questions the coverage scan raised are answered
in `spec.md` under Clarifications.
