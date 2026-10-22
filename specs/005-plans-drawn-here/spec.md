# Feature Specification: Show the plans we offer and let only signed-in users buy one

**Feature Branch**: `005-plans-drawn-here`

**Created**: 2026-10-22

**Status**: Draft

**Serves**: G1 (a project using a supported payment provider gets that provider's pages, looking like the rest of its django-mvp site, without building them), G2 (at least one payment provider is supported, with the records behind its pages kept by this package)

**Roadmap**: R2 — The first backend: the package's own Stripe app

**Issue**: #61

**Input**: The plans page draws the plans itself, from the prices and products in the project's
Stripe catalogue, in place of Stripe's pricing table. Anyone can read them, signed in or not.
Each plan shows its name, its price and how often it is billed, with the description and feature
list the project gave the product in Stripe. Each plan has a way to buy it that works only for a
signed-in person. That way leads to Stripe's own hosted checkout, which the Stripe app starts for
the person's account, so a purchase tied to no account cannot be made from this page. A visitor
who is not signed in and picks a plan is sent to sign in, and comes back to the plan they picked.
The catalogue is read from Stripe and kept in the project's cache rather than copied into the
database. A change in Stripe's dashboard reaches the page through the Stripe app's webhook, and
the cache also expires on its own. The plans are built from components a project can place on a
page of its own, or replace one at a time. The pricing table, its component and its settings are
removed, and specification 003 is brought up to date with the plans page as it now is.

## Clarifications

### Session 2026-10-22

The coverage scan found five ambiguities. Each was answered from the intake discussion, the
constitution and Stripe's published behaviour. Longer rationale is in `decisions.md`.

- **Q: Is a plan a product or a price? A product such as "Pro" often has a monthly and a yearly
  price.**
  A: Every price on offer is a plan a person can buy, shown under its product. A product with a
  monthly and a yearly price offers both, each with its own way to buy it. How the two are laid
  out, side by side or behind a switch, is the sketch's to decide. Recorded as FR-002.

- **Q: Which prices are on offer?**
  A: Every active recurring price of an active product, with a fixed amount, in the price's own
  currency. One-off, metered and tiered prices are left off, because the package bills
  subscriptions only and a tiered price has no single amount to show. Recorded as FR-003.

- **Q: Where does a visitor who signs in after picking a plan land: back on the plans page, or
  straight in Stripe's checkout?**
  A: Back on the plans page, with the plan they picked ready to buy. Starting a checkout is a
  submission made by a signed-in person from a page they can see, never a side effect of
  following a link. Recorded as FR-010.

- **Q: What does someone who already subscribes see?**
  A: Every plan, and they can buy any of them, as before (ADR 0012). The plan they already hold
  is marked as theirs, and its way to buy leads to their user subscriptions page instead of a
  second checkout for the same price. Recorded as FR-013.

- **Q: What happens when the catalogue cannot be read: no secret key, Stripe unreachable, or no
  prices on offer?**
  A: The page says the plans cannot be shown, or that none are on offer, and nothing raises. A
  catalogue already in the cache is shown while it lasts. Recorded as FR-016 and FR-017.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A visitor reads the plans on offer (Priority: P1)

Anyone opens the plans page, signed in or not, and sees every plan the project offers: its name,
its price in its own currency, how often it is billed, and the description and features the
project gave it in Stripe. When there is nothing to show, because the project has not configured
Stripe, Stripe cannot be reached or nothing is on offer, they are told so instead of looking at
an empty page.

**Why this priority**: It is the feature. A visitor deciding whether to sign up can see what
they would pay before making an account, which the pricing table could not allow.

**Independent Test**: With a catalogue of two products, one with a monthly and a yearly price,
open the plans page signed out. Every price is on it with its product's name, amount, frequency,
description and features. Then open it with no secret key configured, with Stripe failing and
with an empty catalogue. Each says why there is nothing to choose, and none raises.

**Acceptance Scenarios**:

1. **Given** a project whose Stripe catalogue has active recurring prices, **When** any visitor
   opens the plans page, **Then** every one of those prices is shown with its product's name, its
   amount in its own currency and its billing frequency.
2. **Given** a product with a description and a list of features in Stripe, **When** the page
   renders, **Then** that description and every one of those features are shown with its prices.
3. **Given** a product with no description or no features, **When** the page renders, **Then**
   its prices are still shown, and nothing stands in for what is missing.
4. **Given** a price in a zero-decimal currency such as JPY, or a three-decimal currency, **When**
   the page renders, **Then** its amount is shown in that currency's own unit.
5. **Given** an archived product, an inactive price, a one-off price, a metered price or a tiered
   price, **When** the page renders, **Then** it is not shown.
6. **Given** a visitor who is not signed in, **When** they open the plans page, **Then** they see
   the plans, without being sent to sign in.
7. **Given** the page renders, **When** its output is read, **Then** it contains no pricing table
   element and no script element pointing at Stripe.
8. **Given** a project with no Stripe secret key configured, or Stripe cannot be reached and no
   catalogue is cached, **When** the plans page renders, **Then** it says the plans cannot be
   shown, nothing raises, and any failure is logged without Stripe's message.
9. **Given** Stripe cannot be reached but a catalogue is cached, **When** the plans page renders,
   **Then** the cached plans are shown.
10. **Given** a catalogue with no price on offer, **When** the plans page renders, **Then** it
    says no plans are on offer.

---

### User Story 2 - A visitor buys a plan, signing in first if they need to (Priority: P1)

A signed-in person picks a plan and is taken to Stripe's hosted checkout to pay for it, tied to
their account. A visitor who is not signed in and picks a plan is sent to sign in, or to create
an account, and comes back to the plans page with that plan ready to buy. After paying, a person
lands on their user subscriptions page and sees the subscription they just bought. Someone who
already subscribes sees the plan they hold marked as theirs, leading to their user subscriptions
page rather than a second checkout for the same price.

**Why this priority**: Without it the plans are something to read and not something to act on,
and it is the reason they are drawn here at all: the pricing table could not stop a signed-out
visitor buying a plan tied to no account.

**Independent Test**: Signed out, pick a plan, sign in, and confirm the plans page comes back
with that plan ready. Pick it, and confirm the checkout Stripe is asked to create is for that
price, carries the user's signed reference, and returns to the user subscriptions page. Then try
to start a checkout signed out without going through the page, and confirm none is created.

**Acceptance Scenarios**:

1. **Given** a signed-in person on the plans page, **When** they pick a plan, **Then** they are
   sent to a Stripe-hosted checkout for that price, carrying their signed reference (ADR 0011).
2. **Given** a signed-in person who already has a Stripe customer, **When** the checkout is
   created, **Then** it is for that customer, so the purchase does not create another one.
3. **Given** a signed-in person with no Stripe customer whose account has an email address,
   **When** the checkout is created, **Then** Stripe is given that address to fill in.
4. **Given** a visitor who is not signed in, **When** they pick a plan, **Then** they are sent
   to the sign-in page, and no checkout is created.
5. **Given** that visitor signs in, or creates an account from the sign-in page, **When** they
   finish, **Then** they are back on the plans page with the plan they picked ready to buy.
6. **Given** a request to start a checkout from someone who is not signed in, made by any route,
   **When** it arrives, **Then** no checkout is created.
7. **Given** the person completes checkout, **When** Stripe sends them back, **Then** they land
   on their user subscriptions page, which shows the subscription they just bought even if
   Stripe's webhook has not arrived yet.
8. **Given** the person leaves checkout without paying, **When** Stripe sends them back, **Then**
   they land on the plans page.
9. **Given** a promotion code the project created in Stripe, **When** the person is in checkout,
   **Then** they can enter it there.
10. **Given** a signed-in person with a current subscription to a price, **When** the plans page
    renders, **Then** that price is marked as theirs and its way to buy leads to their user
    subscriptions page, while every other plan starts a checkout as usual.
11. **Given** a subscription that has ended, **When** the plans page renders, **Then** its price
    is not marked, and can be bought again.
12. **Given** the way to buy a plan, **When** a person reads it with assistive technology,
    **Then** it announces that it leads off the site.
13. **Given** Stripe cannot be asked to create the checkout, **When** the person picks a plan,
    **Then** they are returned to the plans page and told the checkout could not be started, and
    nothing raises.

---

### User Story 3 - A developer changes the plans in Stripe's dashboard (Priority: P2)

A developer adds a price, renames a product, edits its features or archives a plan in Stripe's
dashboard, and the plans page follows without a deployment or a database change.

**Why this priority**: The project manages its plans where it already manages its prices. It is
second because the page has to show plans before changing them matters.

**Independent Test**: Render the plans page, change a product in Stripe, send the matching
verified webhook, and render it again. The change is on the page.

**Acceptance Scenarios**:

1. **Given** the plans page has been shown once, **When** it is shown again, **Then** the
   catalogue is not fetched from Stripe a second time.
2. **Given** a product or price changes in Stripe and Stripe sends the verified webhook for it,
   **When** the plans page is next shown, **Then** it shows the change.
3. **Given** a webhook for a product or price that fails its signature check, **When** it
   arrives, **Then** the plans page is unaffected.
4. **Given** no webhook arrives for a change, **When** the cached catalogue expires, **Then** the
   next showing of the plans page reads it from Stripe again.
5. **Given** a developer who wants the cache to last a different time, **When** they set that in
   the project's settings, **Then** the catalogue expires after that time.
6. **Given** a developer runs the Stripe app's sync command, **When** it finishes, **Then** the
   next showing of the plans page reads the catalogue from Stripe again.

---

### User Story 4 - A developer puts the plans on their own pages, their own way (Priority: P2)

A developer puts the plans on their public landing page as well as the plans page, with the same
ways to buy each one. Where they want one part shown differently, such as a plan's features or
its price, they replace that part and keep the rest as the package draws it.

**Why this priority**: A landing page is where most projects show their prices, and the pricing
table could be placed there, so removing it must not take that away. Replacing one part is what
makes an opinionated default acceptable rather than a ceiling. It is second because the shipped
page comes first.

**Independent Test**: Place the plans in an unrelated template of the project's own, render it
signed out and signed in, and confirm the same plans and ways to buy come out. Override the part
that shows a product's features and confirm the project's markup appears for every plan and every
other part is unchanged.

**Acceptance Scenarios**:

1. **Given** the plans placed in a project's own template, **When** that template renders,
   **Then** it shows the same plans the plans page shows, and the project wrote no view and
   called nothing in Stripe itself.
2. **Given** that placement, **When** a visitor who is not signed in picks a plan there, **Then**
   they are sent to sign in and brought back to the page they picked it on, with that plan ready.
3. **Given** that placement, **When** a signed-in person picks a plan there, **Then** checkout
   starts exactly as it does from the plans page.
4. **Given** a project supplying its own version of one part of a plan, **When** the plans page
   renders, **Then** the project's markup appears in that part for every plan, and every other
   part is as the package draws it.
5. **Given** a part the project replaces, **When** it renders, **Then** it receives the same
   Stripe data the package's own version did, under documented names, in Stripe's own field
   names.
6. **Given** a project placing the plans on one page with its own markup for one part, **When**
   that page renders, **Then** that part is replaced there and nowhere else.
7. **Given** someone reading the documentation, **When** they look for the parts of a plan, the
   data each receives, the settings the page reads and the webhook events it needs, **Then** all
   of them are on a page reachable from the documentation's own navigation.

---

### Edge Cases

- A price whose product is archived but which is itself still active. It is not on offer, because
  its product is not.
- A catalogue with more prices than Stripe returns in one response. Every price on offer is
  shown, not only the first page of them.
- A catalogue with prices in more than one currency. Each is shown in its own currency, and no
  amount is converted.
- A price archived between a visitor loading the page and picking it. No checkout is created, and
  the visitor is returned to the plans page and told the plan is no longer on offer.
- A request to start a checkout for a price that is not on offer: archived, one-off, from another
  account, or made up. No checkout is created.
- A signed-in person whose Stripe customer Stripe no longer has. Checkout is created without it,
  as for a person with no customer, and the signed reference still ties the purchase to them.
- A visitor who picks a plan, signs in, and turns out to hold that price already. The plan comes
  back marked as theirs, leading to their user subscriptions page.
- A project that has not added the product and price events to its Stripe webhook. Changes reach
  the page when the cache expires, which the documentation says.
- A product name, description or feature containing markup. It is shown as text.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The plans page MUST draw the plans from the project's Stripe catalogue, and MUST
  NOT render Stripe's pricing table.
- **FR-002**: Every price on offer MUST be shown with its product's name, its amount in its own
  currency and its billing frequency, under its product, with its own way to buy it.
- **FR-003**: A price MUST be on offer only when it is active, recurring and of a fixed amount,
  and its product is active.
- **FR-004**: A product's description and its list of features, as the project entered them in
  Stripe, MUST be shown with its prices when present.
- **FR-005**: Amounts MUST be shown through the package's existing money formatting, in the
  currency each price carries, never converted between currencies.
- **FR-006**: The plans page MUST be open to every visitor, signed in or not, in any subscription
  state, and MUST NOT send anyone to sign in to read it.
- **FR-007**: A signed-in person picking a plan MUST be sent to a Stripe-hosted checkout for that
  price, created on the server by the Stripe app, carrying the person's signed reference, for
  their existing Stripe customer when they have one, and otherwise with their account's email
  address when it has one.
- **FR-008**: A checkout MUST NOT be created for anyone who is not signed in, whatever route the
  request takes.
- **FR-009**: A checkout MUST NOT be created for a price that is not on offer.
- **FR-010**: A visitor who is not signed in and picks a plan MUST be sent to the sign-in page,
  and after signing in, or creating an account from it, MUST come back to the page they picked
  it on with that plan ready to buy.
- **FR-011**: A completed checkout MUST return the person to their user subscriptions page, which
  MUST show the subscription they just bought without waiting for Stripe's webhook. A checkout
  left without paying MUST return them to the plans page.
- **FR-012**: Checkout MUST accept the project's Stripe promotion codes.
- **FR-013**: For a signed-in person with a current subscription to a price, that price MUST be
  marked as theirs, and its way to buy MUST lead to their user subscriptions page instead of a
  checkout.
- **FR-014**: The catalogue MUST be kept in the project's cache, so the plans page does not ask
  Stripe for it on every showing, and MUST NOT be copied into the database.
- **FR-015**: A verified Stripe webhook about a product or a price MUST clear the cached
  catalogue. The cache MUST also expire on its own after a period with a default, which a project
  can change in its settings. The Stripe app's sync command MUST clear it too.
- **FR-016**: Where the catalogue cannot be read, because no secret key is configured or Stripe
  cannot be reached, and none is cached, the plans page MUST say the plans cannot be shown, MUST
  NOT raise, and MUST log the failure without Stripe's message. A catalogue already cached MUST
  be shown while it lasts.
- **FR-017**: Where the catalogue has no price on offer, the plans page MUST say none are on
  offer.
- **FR-018**: Where Stripe refuses or fails to create a checkout, the person MUST be returned to
  the plans page and told it could not be started, and nothing MUST raise.
- **FR-019**: The plans MUST be built from components that a project can place in a template of
  its own, with the same ways to buy, without writing a view or calling Stripe itself.
- **FR-020**: Each part of a plan, at least its price and its features, MUST be a component of its
  own that a project can replace for the whole site, or for one placement, keeping every other
  part. Each part MUST receive Stripe's data in Stripe's own field names, under documented names.
- **FR-021**: The way to buy a plan MUST announce to assistive technology that it leads off the
  site.
- **FR-022**: The components, the data each receives, the settings the page reads, the webhook
  events it needs and the cache's expiry MUST be documented on a page reachable from the
  documentation's own navigation, and the webhook how-to MUST name the product and price events.

### Key Entities

- **Catalogue**: the prices and products the project offers, as Stripe reports them. Read by the
  Stripe app, kept in the project's cache, never stored in the database and never edited here.
- **Price**: Stripe's record of an amount, a currency and, for a recurring price, how often it is
  billed. What a person buys. Named in Stripe's own words.
- **Product**: Stripe's record of what a price is for, carrying the name, description and feature
  list the project entered. Keeps Stripe's meaning (CONTEXT.md).
- **Plan**: what a reader sees and picks, one price under its product. A presentation term, with
  no record of its own (CONTEXT.md).
- **Checkout**: Stripe's hosted page that takes the payment. Created by the Stripe app for a
  signed-in person, never reproduced here, never seen by this package.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A project that installs the Stripe app, configures its secret key and mounts the
  URLs gets a plans page listing every price on offer in its Stripe catalogue, having written no
  view and no template and created no pricing table.
- **SC-002**: No checkout can be created by a visitor who is not signed in, by any route.
- **SC-003**: A plan bought from the plans page by a signed-in person appears on their user
  subscriptions page as they return from checkout, on their existing Stripe customer when they
  have one.
- **SC-004**: A product or price changed in Stripe's dashboard appears on the plans page the next
  time it is shown after the verified webhook, and within the cache's expiry without one.
- **SC-005**: Showing the plans page again within the cache's expiry makes no request to Stripe.
- **SC-006**: A project replaces one part of a plan with its own markup and every plan shows it,
  with no other change to the project.
- **SC-007**: Every amount on the page is correct in its own currency, including zero-decimal and
  three-decimal currencies.
- **SC-008**: A project with no secret key, an unreachable Stripe or an empty catalogue gets a
  page that says so, with nothing raised.

## Assumptions

- The backend is the package's own Stripe app, `mvp_payments.stripe`. Reading the catalogue,
  keeping it in the cache and creating a checkout are the Stripe app's work. The plans page and
  its components, in the interface, only read what the app hands them (Article XI).
- Plans and prices are managed in Stripe's product catalogue. The description and features are
  Stripe's own product description and marketing features, so a project needs no metadata
  conventions of this package's.
- Plans are listed cheapest first. The sketch may settle on another order before the plan is
  written.
- Taxes, trials and one-off payments stay out of scope (ADR 0010). A project that needs them
  asks, and each becomes its own change.
- Switching between plans a person already holds stays in Stripe's portal (ADR 0008). The user
  subscriptions page's way to another plan is unchanged.
- The sign-in page is django-mvp's, through django-allauth, and returns a person to the address
  they were sent from, including after they create an account.
- This feature replaces Stripe's pricing table on the plans page, which specification 003
  delivered. The pricing table component, its settings and its notice for an unloaded script are
  removed, and specification 003, the constitution's Article XI, ADR 0010, ADR 0012, CONTEXT.md
  and the reference pages are updated in the same pull request to describe the plans page as it
  now is. The package has never been released, so nothing is kept for compatibility (Article XVI).
- A project must add Stripe's product and price events to the webhook endpoint it already points
  at the Stripe app. Without them, changes still arrive when the cache expires.
