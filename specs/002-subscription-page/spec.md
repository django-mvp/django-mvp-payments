# Feature Specification: Show a person the subscription they are on

**Feature Branch**: `002-subscription-page`

**Created**: 2026-09-21

**Status**: Draft

**Serves**: G4 (whatever the installed backend can do, there is a page for it), G1 (adding a backend to a project takes minimal setup and no page-building)

**Roadmap**: R2 — A person can see where they stand

**Issue**: #16

**Input**: The Subscription page shows a signed-in person every subscription they currently hold, what each costs and how often it is billed, and a link out to the provider's portal to manage them. It is built from what the Stripe app records and guesses at nothing else. The deliverable is that page as a reasonable default plus the context and components behind it, so an app developer can change it with a template edit rather than a rewrite. Reading only: nothing here changes a subscription and the page works out no figure of its own.

## Clarifications

### Session 2026-09-21

Six ambiguities were found by the coverage scan and answered from the intake discussion, the
Stripe app's own behaviour and the project's standards document. Longer rationale is in
`decisions.md`.

- **Q: A person can hold several subscriptions, and several of the statuses the Stripe app stores
  describe one that is over. Which of them does a page about what someone is "currently"
  subscribed to show?**
  A: Every one the Stripe app holds as current, meaning every status except the two that mean
  it has finished, cancelled and incomplete-expired. A subscription that is past due, unpaid,
  incomplete or paused is still one the person has, and this page is where they see that and
  reach Stripe's portal to put it right. Taking the app's answer rather than inventing a second
  one is what keeps this page agreeing with the rest of the application. The page lists every such subscription rather than assuming there is
  exactly one. Recorded as FR-001.

- **Q: What is a plan's name?**
  A: The name of the product the subscription is for, which is what the Stripe app records. It
  keeps no price nickname. Recorded as FR-003.

- **Q: What does "a link to the provider's portal" mean, given that the interface layer may not
  call a provider?**
  A: The Stripe app mounts a billing-portal view with the package's URLs. A control on the page
  posts to it, it asks Stripe for a portal session for the signed-in person's customer, and it
  answers with the session's address, which the page's script follows. The page is told where that
  view is mounted by reversing its name, never by assuming an address. Recorded as FR-005 and
  FR-006.

- **Q: Does a person with no current subscription still get the way through to the provider?**
  A: No. A portal session is minted for an existing customer, so for someone with no customer, or
  nothing subscribed, there is nothing on the other side of the link, and the view refuses a direct
  post. The page says plainly that there is no current subscription instead. Recorded as FR-008.

- **Q: Does the page say what a plan grants inside the application?**
  A: No. The Stripe app records no features, so there is nothing to read. A project that keeps
  its own record of what each product grants places it beside the plan in a template of its own.
  Recorded as FR-009.

- **Q: What does the page do with a status it has no particular treatment for?**
  A: Shows it. Stripe adds statuses over time and the app stores whatever it sends, so a page that
  only renders the ones known when it was written goes silently blank on the first new one.
  Recorded as FR-004.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The page says what you are subscribed to (Priority: P1)

Someone signed in to a project that has installed this package and the Stripe app opens the
Subscription page in the Account Center. They are on a paid plan. The page names the plan, what it
costs and how often they are charged for it, the state the subscription is in, and the period it is
in now. They wrote nothing and their project supplied no template.

**Why this priority**: It is the page. Every other story here qualifies it, extends it or gives it
away to the project.

**Independent Test**: Sign in as a person with a current subscription in the Stripe app's records and
open the page. Everything named above is on it.

**Acceptance Scenarios**:

1. **Given** a signed-in person with one current subscription, **When** they open the subscription
   page, **Then** the plan's name, its recurring amount with its currency, its billing frequency
   and its status are all shown.
2. **Given** that subscription has a billing period recorded, **When** the page renders, **Then**
   the period it is currently in is shown.
3. **Given** a signed-in person with more than one current subscription, **When** the page
   renders, **Then** each is shown with its own plan, amount, frequency and status.
4. **Given** subscriptions in different currencies, **When** the page renders, **Then** each shows
   its own amount and no combined figure appears anywhere.
5. **Given** the Stripe app also holds a current subscription for somebody else, **When** the page
   renders for this person, **Then** only their own appears.

---

### User Story 2 - Managing it happens at the provider (Priority: P1)

The same person wants to change their card, read an invoice or cancel. The page tells them their
subscription is managed by the provider and takes them there. Nothing on this page changes anything
about their subscription.

**Why this priority**: Without it the page is a dead end for everyone whose reason for opening it
was to do something. It is also the smallest honest version of the whole page: a person who is told
who manages their subscription and how to reach them has been served, even before anything else
renders.

**Independent Test**: Open the page as a person with a current subscription and follow the way
through. It arrives at the provider's own portal for that person.

**Acceptance Scenarios**:

1. **Given** a signed-in person with a current subscription, **When** they open the page, **Then**
   it says the subscription is managed by the provider and offers a way through to it.
2. **Given** they take that way through, **When** the Stripe app answers with a portal address,
   **Then** they arrive at the provider's portal.
3. **Given** Stripe cannot produce a portal address, **When** they take that way through, **Then**
   they are told so on the page rather than sent nowhere.

---

### User Story 3 - Several subscriptions at once (Priority: P2)

A person holds more than one subscription, bought separately from the plans page. The page lists
every one of them, each with its own plan, amount, frequency, status and period.

**Why this priority**: Stripe's pricing table starts a new subscription with every purchase, so a
person who buys twice holds two, and a page that showed one would misstate what they pay. It is
second because the single-subscription page works without it.

**Independent Test**: Give a person two current subscriptions and open the page. Both are on it.

**Acceptance Scenarios**:

1. **Given** a person with two current subscriptions, **When** the page renders, **Then** both are
   shown, newest period first.
2. **Given** a person with one current and one ended subscription, **When** the page renders,
   **Then** only the current one is shown.
3. **Given** any number of subscriptions, **When** the page renders, **Then** the number of
   database queries it makes does not change with the number.

---

### User Story 4 - Nothing current to show (Priority: P2)

Someone opens the page who has never subscribed, or whose subscription has ended. They are told
that plainly, on a page that looks finished.

**Why this priority**: It is the majority of readers on most projects, and it is the state a page
built only for the happy path gets wrong.

**Independent Test**: Open the page as a person with no current subscription. The page says so and
shows no empty region where a plan would have been.

**Acceptance Scenarios**:

1. **Given** a signed-in person with no current subscription, **When** they open the page, **Then**
   it says there is none.
2. **Given** that person, **When** the page renders, **Then** no plan, amount, frequency, status or
   period appears.
3. **Given** the Stripe app has no customer for that person, **When** the page renders, **Then** no
   way through to the provider's portal is offered.

---

### User Story 5 - A project makes the page its own (Priority: P3)

Someone building on this package wants a different page: their own wording, their own arrangement,
their own additions beside it. They override the template and keep everything the page was already
given, or they place individual pieces of it inside a page of their own. They write no view and
they query the Stripe app for nothing.

**Why this priority**: It is what makes a default page acceptable rather than a limit. No default
can anticipate what any given project needs, so the honest answer is to make replacing it cheap. It
is third because there is nothing to override until the first four stories exist.

**Independent Test**: Replace the page's template in a project, render the same values from the
context it is given, and confirm nothing else is needed. Then place one of its components in an
unrelated template and confirm it renders on its own.

**Acceptance Scenarios**:

1. **Given** a project supplying its own template for the subscription page, **When** that template
   renders, **Then** every value the shipped page shows is available to it under a documented name.
2. **Given** a project placing one of this page's components in a template of its own, **When** that
   template renders, **Then** the component renders from the attributes it was given.
3. **Given** a project that has overridden the template, **When** it renders, **Then** it needs no
   view, no context processor and no query against the Stripe app of its own.
4. **Given** someone reading the documentation, **When** they look for these components and the
   names the page puts in the context, **Then** both are documented on a page they can reach from
   the documentation's own navigation.

---

### Edge Cases

- A subscription whose price Stripe has since deactivated, or a product since renamed in the
  provider's dashboard. The Stripe app keeps what it last read, and that is what the person is
  paying, so the page shows it unchanged.
- A currency with no minor unit. The amount is presented as that currency is written, not as a
  figure with two decimal places bolted on.
- A price with no fixed amount. The amount is omitted and the rest of the entry still renders.
- A subscription recorded with no billing period. The period is omitted and the rest of the entry
  still renders.
- A person signed out, reaching the page's address directly. They are sent to the project's sign-in
  page, as every page this package contributes except the plans page already does.
- The Stripe app installed but holding no records at all, which is every project's first run. The
  page reads as a person with no current subscription rather than as a failure.
- A person back from paying at the provider before the Stripe app has heard of the payment. The
  page says the payment is being confirmed and checks again, rather than saying there is no
  subscription.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The subscription page MUST show every subscription the Stripe app holds as current
  for the signed-in person, and MUST take the app's own definition rather than applying
  one of its own.
- **FR-002**: For each of those subscriptions the page MUST show its status, and its current
  billing period where the Stripe app recorded one.
- **FR-003**: For each subscription the page MUST show the plan's name, which is the name of the
  product it is for, its recurring amount in the currency the Stripe app recorded, and its billing
  frequency.
- **FR-004**: The page MUST render any status the Stripe app holds, including one it has no
  specific treatment for.
- **FR-005**: The page MUST state that the subscription is managed by the provider, and MUST offer
  a way through to the provider's own management portal.
- **FR-006**: The page MUST obtain the portal address from the Stripe app's billing-portal view,
  and MUST find that view by its URL name rather than assuming its location.
- **FR-007**: The page MUST NOT compute any figure. No total across subscriptions, no proration, no
  next charge, no conversion between currencies. Every figure shown is one the Stripe app recorded.
- **FR-008**: A signed-in person with no current subscription MUST be told so, and MUST be offered
  no way through to the provider.
- **FR-009**: The page MUST show nothing about what a plan grants inside the application, because
  the Stripe app records no features.
- **FR-010**: The page MUST require a signed-in person and MUST show only that person's own
  records. Any finer decision about who may see it remains the host project's.
- **FR-011**: Everything the shipped page renders MUST be available to a project's own template
  under documented names, so that overriding the template needs no view and no query of the
  Stripe app.
- **FR-012**: Each part of the page MUST be a component in the Stripe namespace that renders from
  its own attributes, so that a project can place it in a template of its own.
- **FR-013**: The components this feature adds and the context the page supplies MUST be documented
  on a page a reader can reach from the documentation's own navigation.

### Key Entities

- **Subscription**: the Stripe app's record that this person is signed up to something, carrying a
  status, a billing period, a product name, a price and a billing interval. Displayed here, never
  created or changed.
- **Plan**: what a person reads as the thing they are paying for: a name, an amount, a currency
  and a billing frequency. It is a presentation term. The Stripe app records these on the
  subscription itself.
- **Billing portal**: the provider's own page for changing a payment method, reading invoices and
  cancelling. Reached from here, never reproduced here.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A project that installs this package and the Stripe app and mounts the package's URLs
  gets a subscription page naming the plan, amount, frequency, status and period of every
  subscription, having written no view and no template.
- **SC-002**: A signed-in subscriber reaches the provider's management portal from the subscription
  page in one step.
- **SC-003**: Every figure on the rendered page corresponds to a single value the Stripe app
  recorded, with no figure produced by combining or converting values.
- **SC-004**: A person with no current subscription gets a page that states that, with nothing on
  it left blank and no error raised.
- **SC-005**: A project replaces the page's template and renders the same information without
  adding a view, a context processor or a query against the Stripe app.
- **SC-006**: Every component this feature adds renders correctly when placed on its own in an
  unrelated template, given its attributes.

## Assumptions

- The backend in question is the package's own Stripe app, `mvp_payments.stripe`. The page is built
  from what that app records, and nothing here is designed to fit a second backend that does not
  exist yet. A second backend gets its own namespace and its own page.
- The project has mounted this package's URLs, which carry the Stripe app's billing-portal view
  with them. Without them there is no view to obtain a portal address from, which is the project's
  own configuration rather than something this page can supply.
- The Stripe app keeps its records in step with the provider, through its webhook and its `sync()`.
  This page shows what it finds and does not judge how fresh it is.
- A project that keeps a record of what each product grants has no place for it on this page. It
  places its own list beside the plan in a template of its own.
- The pages, navigation entry and card this feature fills were delivered by the previous feature.
  Nothing here changes how a page arrives, only what is on one of them.
- This package reads the Stripe app's records through the application registry, imports no
  provider library outside that app, holds no state of its own, and reaches no provider from the
  interface layer. Those are standing constraints rather than choices this feature makes.
