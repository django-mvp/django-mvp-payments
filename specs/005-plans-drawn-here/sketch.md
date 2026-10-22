# Sketch — 005 Show the plans we offer and let only signed-in users buy one

## What exists

- **Records.** The Stripe app keeps `Customer` (user, Stripe id) and `Subscription` (price id,
  product name, amount, currency, interval, interval count, status, period). Nothing stores
  products or prices. `Subscription.objects.for_user(user).current()` says which prices a
  person holds now.
- **Ties a purchase to a person.** `Customer.client_reference(user)` builds the signed
  reference (ADR 0011). `Customer.for_user(user)` finds their Stripe customer.
  `BillingReturnView` syncs a customer on the way back from Stripe and lands on the user
  subscriptions page with `?returned=1`, which polls until the change arrives.
- **Money.** `mvp_payments.money.Money` formats a minor-unit amount in its own currency, and
  `<c-stripe.amount>` renders one. `CurrentSubscription.frequency_display` turns an interval
  into words ("every month", "every 3 months").
- **Page.** Before this feature `PlansPageView` rendered `mvp_payments/stripe/plans.html`
  inside the Account Center, routed by the Stripe contribution, open to everyone. `<c-stripe.plans-unavailable>` is the "not available" empty state.
- **Components to compose.** `<c-mvp.card>` (title, badges, footer slots), `<c-mvp.grid>`,
  `<c-join>`, `<c-button>`, `<c-badge>`, `<c-alert>`, `<c-icon>`, and
  `<c-mvp.page.list.empty>` for empty states. Alpine.js is already loaded by django-mvp's base
  template.
- **Planning notes that bear on the screens.** Plans are Cotton parts, each taking Stripe's own
  fields. Alpine switches between monthly and yearly prices on cards the server has drawn.

## What the screens need from the code

- Every price on offer, as Stripe returns it, with its product expanded: `id`, `unit_amount`,
  `currency`, `recurring.interval`, `recurring.interval_count`, and the product's `id`, `name`,
  `description` and `marketing_features`.
- The prices ordered with each product's prices together, products cheapest first.
- The distinct billing frequencies on offer, each with a label for the switch, and which one
  the switch starts on: the frequency of the plan in `?plan=`, otherwise the shortest.
- The price ids the signed-in person currently holds.
- The price id the visitor picked before signing in (`?plan=`), so its card can stand out.
- Whether the reader is signed in, the sign-in address, the checkout address, the user
  subscriptions address, and the path of the page the plans are on, so sign-in and a cancelled
  checkout come back to it.
- A public address for the plans page outside the Account Center. The sketch adds
  `mvp_payments.plans_urls`, which the demo mounts at `/plans/` with a second include line,
  and takes the plans page out of the Stripe contribution. The plan decides how a project
  mounts it, given Article XIII's single include.
- A way to put all of that in any template without a view: the sketch uses a template tag,
  `{% stripe_plans as plans %}`, and the plans page puts the same thing in its context.
- Two notices on return to the page: the checkout could not be started, and the plan picked is
  no longer on offer.

## What the sketch faked

- The catalogue. `mvp_payments/namespaces/stripe_catalogue.py` returns hard-coded Stripe-shaped
  prices. `?sketch=` picks one: the default (three products, monthly and yearly), `single`,
  `many`, `currencies`, `empty`, `unavailable`. The build reads Stripe through the Stripe app
  and caches it (FR-014), and the file is deleted.
- The checkout. `CheckoutView` only redirects back with `?sketch_checkout=` and an info alert
  saying so. The build creates the Stripe checkout session (FR-007, FR-009, FR-012) and
  redirects to it.
- The two failure notices are reached with `?sketch=checkout-failed` and `?sketch=plan-gone`.
  The build sets them from what actually happened.
- The demo's seeded Basic subscription uses the price id `price_demo_regular`, which the fake
  catalogue reuses so the "current plan" state shows for `regular.user`.
- Replacing one part for a single placement (US-4, scenario 6) is not drawn. The parts are
  separate components, so replacing one for the whole site works now.
- The pricing table component, its settings, `pricing_table.js` and the demo's pages for it
  are still in the tree. The build removes them.

## What was ruled by eye

Ruled by Sam:

- The plans page is public, so it is not under the account address. It lives at `/plans/`,
  outside the Account Center, with an entry in the demo's sidebar (round 1).

- Round 2 approved as shown (2026-10-22): every taste decision below stands.

Taste decisions, approved by Sam in round 2:

- One card per price, grouped by billing frequency behind a switch, the pattern Stripe's own
  pricing table uses. Without JavaScript every frequency shows, each under its own heading.
- The switch is shown only when there is more than one billing frequency.
- Card order: name, then price, then description and features, then the way to buy at the
  bottom. The price sits straight under the name so prices line up across a row whatever the
  descriptions' lengths, and the buttons line up along the bottom.
- Full-width buttons in the cards.
- The switch and the checkout note align left with the page title.
- Billing frequencies in the switch run shortest first.
- Price shown large, with the frequency in words beside it.
- The plan picked before signing in is outlined in the primary colour, and the page scrolls to it.
- A plan the person holds carries a "Current" badge and a "Manage" button to the user
  subscriptions page in place of "Choose".
- One line under the plans says payment is taken on Stripe's checkout page. Every "Choose"
  button is described by it, so a screen reader announces that it leads off the site.
- Two columns from the medium breakpoint, three from extra large.
