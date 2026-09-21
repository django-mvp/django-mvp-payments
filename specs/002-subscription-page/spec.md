# Feature Specification: Show a person the subscription they are on

**Feature Branch**: `002-subscription-page`

**Created**: 2026-09-21

**Status**: Draft

**Serves**: G4 (whatever the installed backend can do, there is a page for it), G1 (adding a backend to a project takes minimal setup and no page-building)

**Roadmap**: R2 — A person can see where they stand

**Issue**: #16

**Input**: The Subscription page shows a signed-in person the plan they are currently on, what that plan gets them inside the app, and a link out to the provider's portal to manage it. It is built from what the installed backend records and guesses at nothing else. The deliverable is that page as a reasonable default plus the context and components behind it, so an app developer can change it with a template edit rather than a rewrite. Reading only: nothing here changes a subscription and the page works out no figure of its own.

## Clarifications

### Session 2026-09-21

Six ambiguities were found by the coverage scan and answered from the intake discussion, the
backend's own behaviour and the project's standards document. Longer rationale is in
`decisions.md`.

- **Q: A person can hold several subscriptions, and several of the statuses the backend stores
  describe one that is over. Which of them does a page about what someone is "currently"
  subscribed to show?**
  A: Whichever the backend itself calls current. It already draws that line and applies it
  everywhere else it answers questions about a person: a subscription counts as current while it
  is active, on trial, or past due, and does not once it has been cancelled, has ended or has gone
  unpaid. Taking the backend's answer rather than inventing a second one is what keeps this page
  agreeing with the rest of the application. The page renders every current subscription it is
  given rather than assuming there is exactly one. Recorded as FR-001.

- **Q: What is a plan's name, when the backend records both a product name and a price nickname?**
  A: The nickname where the project set one, and the product's name otherwise. The nickname exists
  to be displayed and is the more specific of the two, so a project that took the trouble to set
  it meant it to be read. Recorded as FR-003.

- **Q: What does "a link to the provider's portal" mean, given that this package may not call a
  provider?**
  A: The backend already exposes an endpoint that mints a portal session for the signed-in person
  and answers with its address. The page asks the backend, and the backend talks to the provider.
  Where that endpoint lives is the project's decision, because the project is what mounts the
  backend's URLs, so the page is told its location rather than assuming one. Recorded as FR-005
  and FR-006.

- **Q: Does a person with no current subscription still get the way through to the provider?**
  A: No. A portal session is minted for an existing customer, so for someone the backend has no
  customer record for there is nothing on the other side of the link. The page says plainly that
  there is no current subscription instead. Recorded as FR-008.

- **Q: Features are recorded against a product, and the backend can also answer "every feature
  this person has access to" across all their subscriptions. Which does the page show?**
  A: The features of the plan being displayed, beside that plan. The page is about what a person
  is subscribed to, and a combined list read beside one plan's name would attribute to that plan
  things a different subscription pays for. Recorded as FR-009.

- **Q: What does the page do with a status the backend records that it has no particular treatment
  for?**
  A: Shows it. The backend stores whatever the provider sends and the provider adds statuses over
  time, so a page that only renders the ones known when it was written goes silently blank on the
  first new one. Recorded as FR-004.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The page says what you are subscribed to (Priority: P1)

Someone signed in to a project that has installed this package alongside a payment backend opens
the Subscription page in the Account Center. They are on a paid plan. The page names the plan, what
it costs and how often they are charged for it, the state the subscription is in, and the period it
is in now. They wrote nothing and their project supplied no template.

**Why this priority**: It is the page. Every other story here qualifies it, extends it or gives it
away to the project.

**Independent Test**: Sign in as a person with a current subscription in the backend's records and
open the page. Everything named above is on it.

**Acceptance Scenarios**:

1. **Given** a signed-in person whose backend records one current subscription, **When** they open
   the subscription page, **Then** the plan's name, its recurring amount with its currency, its
   billing frequency and its status are all shown.
2. **Given** that subscription has a billing period recorded, **When** the page renders, **Then**
   the period it is currently in is shown.
3. **Given** a signed-in person whose backend records more than one current subscription, **When**
   the page renders, **Then** each is shown with its own plan, amount, frequency and status.
4. **Given** a subscription covering more than one priced item, **When** the page renders, **Then**
   each item is shown with its own amount and no combined figure appears anywhere.
5. **Given** the backend also records a current subscription for somebody else, **When** the page
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
2. **Given** they take that way through, **When** the backend answers with a portal address,
   **Then** they arrive at the provider's portal.
3. **Given** the backend cannot produce a portal address, **When** they take that way through,
   **Then** they are told so on the page rather than sent nowhere.

---

### User Story 3 - What the plan gets you in the app (Priority: P2)

The project has recorded, against each of its products, the features that product grants inside the
application. A person reading their subscription sees what their plan entitles them to, in the
project's own words where it supplied them.

**Why this priority**: It is the part a person cannot work out for themselves, and the part no
provider's own page can ever show, because the provider does not know what the application does.
It is second because a project that recorded no features still has a working page without it.

**Independent Test**: Record features against a product, subscribe a person to a price of that
product, and open the page. The features are listed under that plan.

**Acceptance Scenarios**:

1. **Given** a plan whose product has features recorded against it, **When** the page renders,
   **Then** those features are listed with the plan.
2. **Given** a feature the project gave a description, **When** it is listed, **Then** the
   description is what is shown.
3. **Given** a feature the project gave no description, **When** it is listed, **Then** its
   identifier is shown rather than an empty line.
4. **Given** a plan whose product has no features recorded, **When** the page renders, **Then**
   nothing about features appears for it.

---

### User Story 4 - Nothing current to show (Priority: P2)

Someone opens the page who has never subscribed, or whose subscription has ended. They are told
that plainly, on a page that looks finished.

**Why this priority**: It is the majority of readers on most projects, and it is the state a page
built only for the happy path gets wrong.

**Independent Test**: Open the page as a person the backend records no current subscription for.
The page says so and shows no empty region where a plan would have been.

**Acceptance Scenarios**:

1. **Given** a signed-in person the backend records no current subscription for, **When** they open
   the page, **Then** it says there is none.
2. **Given** that person, **When** the page renders, **Then** no plan, amount, frequency, status,
   period or feature list appears.
3. **Given** the backend has no customer record for that person, **When** the page renders,
   **Then** no way through to the provider's portal is offered.

---

### User Story 5 - A project makes the page its own (Priority: P3)

Someone building on this package wants a different page: their own wording, their own arrangement,
their own additions beside it. They override the template and keep everything the page was already
given, or they place individual pieces of it inside a page of their own. They write no view and
they query the backend for nothing.

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
   view, no context processor and no query against the backend of its own.
4. **Given** someone reading the documentation, **When** they look for these components and the
   names the page puts in the context, **Then** both are documented on a page they can reach from
   the documentation's own navigation.

---

### Edge Cases

- A subscription whose plan refers to a price the provider has since deactivated, or a product
  since renamed in the provider's dashboard. The backend keeps what it recorded, and that is what
  the person is paying, so the page shows it unchanged.
- A currency with no minor unit. The amount is presented as that currency is written, not as a
  figure with two decimal places bolted on.
- A subscription the backend recorded with no billing period. The period is omitted and the rest of
  the entry still renders.
- A person signed out, reaching the page's address directly. They are sent to the project's sign-in
  page, as every page this package contributes already does.
- The backend installed but holding no records at all, which is every project's first run. The page
  reads as a person with no current subscription rather than as a failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The subscription page MUST show every subscription the installed backend reports as
  current for the signed-in person, and MUST take the backend's own definition of current rather
  than applying one of its own.
- **FR-002**: For each of those subscriptions the page MUST show its status, and its current
  billing period where the backend recorded one.
- **FR-003**: For each priced item a subscription covers the page MUST show the plan's name, its
  recurring amount in the currency the backend recorded, and its billing frequency. The plan's name
  is the price's nickname where there is one and the product's name otherwise.
- **FR-004**: The page MUST render any status the backend holds, including one it has no specific
  treatment for.
- **FR-005**: The page MUST state that the subscription is managed by the provider, and MUST offer
  a way through to the provider's own management portal.
- **FR-006**: The page MUST obtain the portal address from the installed backend, and MUST be told
  where that backend's endpoint is rather than assuming its location.
- **FR-007**: The page MUST NOT compute any figure. No total across items, no proration, no next
  charge, no conversion between currencies. Every figure shown is one the backend recorded.
- **FR-008**: A signed-in person the backend reports no current subscription for MUST be told so,
  and MUST be offered no way through to the provider.
- **FR-009**: Where the project has recorded features against a plan's product, the page MUST list
  them with that plan, showing the project's description of a feature where it supplied one and the
  feature's identifier otherwise.
- **FR-010**: The page MUST require a signed-in person and MUST show only that person's own
  records. Any finer decision about who may see it remains the host project's.
- **FR-011**: Everything the shipped page renders MUST be available to a project's own template
  under documented names, so that overriding the template needs no view and no query of the
  backend.
- **FR-012**: Each part of the page MUST be a component in the backend's namespace that renders
  from its own attributes, so that a project can place it in a template of its own.
- **FR-013**: The components this feature adds and the context the page supplies MUST be documented
  on a page a reader can reach from the documentation's own navigation.

### Key Entities

- **Subscription**: the backend's record that this person is signed up to something, carrying a
  status, a billing period and the priced items it covers. Displayed here, never created or
  changed.
- **Plan**: what a person reads as the thing they are paying for: a name, an amount, a currency
  and a billing frequency. It is a presentation term. The backend records it as a price belonging
  to a product.
- **Feature**: something the plan grants inside the application, recorded by the project against a
  product. It has an identifier and, where the project supplied one, a description.
- **Billing portal**: the provider's own page for changing a payment method, reading invoices and
  cancelling. Reached from here, never reproduced here.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A project that installs this package beside the backend and mounts its URLs gets a
  subscription page naming the plan, amount, frequency, status and period, having written no view
  and no template.
- **SC-002**: A signed-in subscriber reaches the provider's management portal from the subscription
  page in one step.
- **SC-003**: Every figure on the rendered page corresponds to a single value the backend recorded,
  with no figure produced by combining or converting values.
- **SC-004**: A person with no current subscription gets a page that states that, with nothing on
  it left blank and no error raised.
- **SC-005**: A project replaces the page's template and renders the same information without
  adding a view, a context processor or a query against the backend.
- **SC-006**: Every component this feature adds renders correctly when placed on its own in an
  unrelated template, given its attributes.

## Assumptions

- The backend in question is drf-stripe-subscription, the namespace this package ships today. The
  page is built from what that backend records, and nothing here is designed to fit a second
  backend that does not exist yet. A second backend gets its own namespace and its own page.
- The project has mounted the backend's URLs. Without them there is no endpoint to obtain a portal
  address from, which is the project's own configuration rather than something this page can
  supply.
- The project keeps the backend's records in step with the provider, which is the backend's job and
  its reason for existing. This page shows what it finds and does not judge how fresh it is.
- Features are recorded against products by the project, as the backend provides for. A project
  that records none simply has no feature list, which is a valid page.
- The pages, navigation entry and card this feature fills were delivered by the previous feature.
  Nothing here changes how a page arrives, only what is on one of them.
- This package reads the backend's records through the application registry and imports nothing
  from it, holds no state, and reaches no provider from the server. Those are standing constraints
  rather than choices this feature makes.
