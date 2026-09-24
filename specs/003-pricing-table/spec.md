# Feature Specification: Offer plans through the provider's own pricing table

**Feature Branch**: `003-pricing-table`

**Created**: 2026-09-22

**Status**: Draft

**Serves**: G1 (adding a backend to a project takes minimal setup and no page-building), G2 (both a native interface and the provider's own embed are first-class ways to get a working page)

**Roadmap**: R3 — A person can choose a plan and start paying

**Issue**: #24

**Input**: A payment component in the drf-stripe namespace that renders the provider's own pricing table, placeable by a project on any page of its own and also filling the Plans page this package already contributes to the Account Center. Both routes render the same component, so there is one thing to override. The component emits the provider's pricing-table element and its attributes only, never the provider's script tag, which the host project loads however it already manages its frontend. The pricing table identifier and publishable key reach the component as attributes; the shipped Plans page reads both from the project's settings and passes them through, and says plainly when they are absent rather than emitting an element that cannot work. When a person is signed in, the component passes their account email address to the pricing table, because the backend matches a provider customer to a Django user by email address alone and a purchase made under a different address attaches to nobody. No plan selection is built from the backend's own records: a project that wants its own markup overrides the component or the page template.

## Clarifications

### Session 2026-09-22

The coverage scan found five ambiguities. Each was answered from the intake discussion, the
provider's published behaviour and the backend's own source. Longer rationale is in
`decisions.md`.

- **Q: The provider's dashboard hands a project two things together, a script tag and an element.
  Which of them does this package emit?**
  A: The element and its attributes only. Loading a third-party script is the project's decision
  about its own frontend, and a package that injected one would add an external origin to every
  project that installed it. This is the standing rule for provider libraries in this repository,
  applied to an embed for the first time. Recorded as FR-002.

- **Q: The shipped page has no template author to pass it attributes. Where do its pricing table
  identifier and publishable key come from?**
  A: The project's settings, read by the page and handed to the component as attributes. The page
  already reads the backend's portal endpoint from the same place, so this is the established way
  a shipped page learns something only the project knows. The component itself still takes both as
  attributes and reads no settings, which keeps it placeable anywhere. This narrows a standing rule
  that currently forbids reading a publishable key from settings anywhere in this package, and the
  reasoning is in `decisions.md`. Recorded as FR-003 and FR-004.

- **Q: A person buys through the provider's hosted checkout, which this package never sees. What
  makes the resulting subscription theirs?**
  A: Their email address, passed to the pricing table when they are signed in. The backend matches
  a provider customer to an application user on email address alone and reads no other identifier,
  so a person who types a different address at checkout gets a subscription attached to nobody, or
  a duplicate account where the project configured the backend to create one. Passing the address
  they are signed in with is what closes that gap. Where nobody is signed in, nothing is passed and
  the person supplies their own address at checkout. Recorded as FR-005.

- **Q: What does a project see before it has supplied a pricing table identifier and a publishable
  key, which is every project's first run?**
  A: A page that says the plans cannot be shown yet. An element emitted without them renders as
  empty space with nothing in the page to explain it, so the absence is stated rather than shown.
  Recorded as FR-007.

- **Q: Does the Plans page still require a signed-in person, given that the embed reflects nobody?**
  A: Yes. It is one of the Account Center's pages and every page this package contributes requires
  sign-in. The component carries no such requirement, which is what lets a project place it on a
  public landing page. Recorded as FR-008 and FR-009.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plans arrive on the page without building one (Priority: P1)

Someone building on this package installs it beside the payment backend, mounts its URLs, creates a
pricing table in the provider's dashboard and puts its identifier and their publishable key in
their settings. The Plans page in the Account Center now shows their plans, priced and styled as
the provider renders them, and a person can pick one. No template was written and no view exists in
the project.

**Why this priority**: It is the feature. Everything else here qualifies it, extends it or gives it
away to the project.

**Independent Test**: Configure a project with a pricing table identifier and publishable key, sign
in, open the Plans page. The provider's table is on it and its buttons lead to the provider's
checkout.

**Acceptance Scenarios**:

1. **Given** a project that has supplied a pricing table identifier and a publishable key, **When**
   a signed-in person opens the Plans page, **Then** the provider's pricing table element is
   rendered carrying both values.
2. **Given** that page, **When** it renders, **Then** it contains no script element pointing at the
   provider.
3. **Given** the project has loaded the provider's script as part of its own frontend, **When** the
   page is opened in a browser, **Then** the table displays the project's plans and each plan
   offers a way to subscribe.
4. **Given** a person takes one of those ways, **When** they do, **Then** they arrive at the
   provider's own checkout without passing through any page of this package.
5. **Given** a visitor who is not signed in, **When** they go to the Plans page's address directly,
   **Then** they are sent to the project's sign-in page, as every page this package contributes
   already does.
6. **Given** the page renders, **When** its output is read, **Then** no amount, currency or billing
   frequency produced by this package appears anywhere on it. Every price a reader sees comes from
   the provider.

---

### User Story 2 - A purchase belongs to the person who made it (Priority: P1)

A signed-in person picks a plan and pays. Their subscription appears on their own subscription page
afterwards, because the customer the provider created is matched to their account.

**Why this priority**: Without it the feature is worse than absent. A person pays, sees nothing
change, and the project has a payment it cannot attribute. It is equal in priority to the first
story because a plan chooser that loses the purchase has not delivered anything.

**Independent Test**: Sign in as a person with a known email address, open the page, and confirm
the address the pricing table receives is the one on their account.

**Acceptance Scenarios**:

1. **Given** a signed-in person whose account carries an email address, **When** the component
   renders, **Then** the provider's element carries that address.
2. **Given** a signed-in person whose account carries no email address, **When** the component
   renders, **Then** no address is carried and the element is otherwise unchanged.
3. **Given** nobody is signed in, **When** the component renders, **Then** no address is carried.
4. **Given** the component is placed with an address supplied as an attribute, **When** it renders,
   **Then** that address is used rather than the signed-in person's.

---

### User Story 3 - The same plans on a page of the project's own (Priority: P2)

Someone building on this package wants plans on their public landing page as well as inside the
Account Center. They place the component in their own template with their own attributes. It
renders the same table, for a reader who is not signed in.

**Why this priority**: It is the second of the two places a project puts plans, and the one the
Account Center cannot serve, because a landing page has no signed-in person. It is second because
the shipped page has to exist before there is anything worth placing elsewhere.

**Independent Test**: Put the component in an unrelated template with a pricing table identifier
and publishable key, render it for an anonymous visitor, and confirm the element comes out
complete.

**Acceptance Scenarios**:

1. **Given** the component placed in a project's own template with both values as attributes,
   **When** that template renders, **Then** the provider's element is produced with those values.
2. **Given** that placement, **When** it renders for a visitor who is not signed in, **Then** it
   renders without requiring one.
3. **Given** that placement, **When** it renders, **Then** it needs no view, no context processor
   and no query against the backend.

---

### User Story 4 - Nothing to show yet, said plainly (Priority: P2)

A project has installed everything but has not supplied a pricing table identifier or a publishable
key, or has not loaded the provider's script. A reader is told the plans cannot be shown instead of
looking at empty space.

**Why this priority**: It is every project's first run, and the failure it prevents is silent. The
provider's element renders as nothing at all when it cannot work, which reads as a broken page with
no clue in it.

**Independent Test**: Open the Plans page with no pricing table identifier configured. The page
states the plans are unavailable and emits no provider element.

**Acceptance Scenarios**:

1. **Given** a project that has supplied no pricing table identifier, **When** the Plans page
   renders, **Then** it states that plans cannot be shown and emits no provider element.
2. **Given** a project that has supplied no publishable key, **When** the Plans page renders,
   **Then** the same applies.
3. **Given** both values are present but the provider's script has not been loaded by the project,
   **When** a reader opens the page, **Then** they are told the plans could not be loaded rather
   than shown an empty region.
4. **Given** any of those states, **When** the page renders, **Then** nothing raises and the rest
   of the page is unaffected.

---

### User Story 5 - A project supplies its own markup instead (Priority: P3)

Someone wants plans rendered their way rather than the provider's: their own layout, their own
copy, their own comparison. They replace the component, or the page template that holds it, and
keep everything else the package gives them.

**Why this priority**: It is what makes an opinionated default acceptable rather than a ceiling. It
is third because there is nothing to replace until the default exists.

**Independent Test**: Override the component in a project and confirm the Plans page renders the
project's markup with no other change. Then override the page template and confirm the same.

**Acceptance Scenarios**:

1. **Given** a project supplying its own version of the component, **When** the Plans page renders,
   **Then** the project's markup is what appears.
2. **Given** a project supplying its own template for the Plans page, **When** it renders, **Then**
   every value the shipped page would have used is available to it under a documented name.
3. **Given** either override, **When** it renders, **Then** the project needs no view and no query
   against the backend.
4. **Given** someone reading the documentation, **When** they look for the component, its
   attributes, the settings the page reads and how the provider's script is expected to arrive,
   **Then** all of them are documented on a page reachable from the documentation's own navigation.

---

### Edge Cases

- A pricing table identifier that does not belong to the account the publishable key identifies.
  The provider rejects the pairing and renders nothing, which the unavailable state covers without
  this package inspecting either value.
- A pricing table the project has since archived in the provider's dashboard. What the reader sees
  is the provider's to decide, and this package shows whatever it renders.
- A person signed in with an address that already belongs to a different provider customer. The
  backend matches by address, so the existing customer is used. That is the backend's behaviour and
  not something this page overrides.
- A project that places the component more than once on the same page. Each placement renders its
  own element, and the provider's script brings all of them to life.
- A reader with the provider's origin blocked. The element never comes to life, which is the same
  condition as the script not being loaded and reads the same way.
- A current subscriber who reaches the Plans page, by its address or an old link. They are told
  they already have a subscription and sent to where plans are changed, never shown a table that
  would sell them a second one (FR-014).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST ship a component in the drf-stripe namespace that renders the
  provider's pricing table, and the Plans page it already contributes MUST render that same
  component rather than markup of its own.
- **FR-002**: The component MUST emit the provider's pricing table element and its attributes only,
  and MUST NOT emit a script element or otherwise cause the provider's library to be fetched.
  Loading that library remains the host project's decision.
- **FR-003**: The component MUST take the pricing table identifier and the publishable key as
  attributes, and MUST NOT read either from the project's settings.
- **FR-004**: The Plans page MUST read the pricing table identifier and the publishable key from
  the project's settings and pass them to the component as attributes.
- **FR-005**: Where a person is signed in and their account carries an email address, the component
  MUST pass that address to the provider's element, so that the customer the provider creates
  matches the person who is signed in. An address supplied as an attribute takes precedence, and
  where there is neither, none is passed.
- **FR-006**: The component MUST render for a reader who is not signed in, so that a project can
  place it on a public page.
- **FR-007**: Where the pricing table identifier or the publishable key is absent, the Plans page
  MUST state that plans cannot be shown and MUST emit no provider element.
- **FR-008**: The Plans page MUST continue to require a signed-in person, as every page this
  package contributes does.
- **FR-009**: The component MUST impose no sign-in requirement of its own.
- **FR-010**: A reader MUST be told when the provider's element could not be brought to life,
  rather than being shown an empty region with nothing to explain it.
- **FR-011**: The package MUST NOT read, compute or display anything about what a plan costs. Every
  price a reader sees is rendered by the provider.
- **FR-012**: A project MUST be able to replace the component, or the Plans page template that
  holds it, and get its own markup without writing a view or querying the backend.
- **FR-013**: The component, its attributes, the settings the Plans page reads and the project's
  responsibility for loading the provider's script MUST be documented on a page a reader can reach
  from the documentation's own navigation.
- **FR-014**: The Plans page MUST NOT render the provider's pricing table for a person who already
  has a current subscription. It MUST instead say that they already have one and lead them to the
  subscription page. The pricing table cannot show which plan they are on, and a purchase through
  it starts a second subscription beside the first.
- **FR-015**: The subscription page's way to another plan MUST, for a current subscriber, lead to
  the provider's own plan-change screen for their existing subscription, through an endpoint the
  project names in its settings, and MUST NOT lead to the Plans page. Where the project names no
  such endpoint, no plan-change control is offered to a subscriber. A person with no current
  subscription is led to the Plans page.

### Key Entities

- **Pricing table**: the provider's published embed, built and configured in the provider's own
  dashboard from the provider's catalogue. Identified by a value that dashboard issues. Rendered
  here, never composed here.
- **Publishable key**: the provider's public identifier for an account, which the provider's own
  documentation passes in markup. Supplied by the project. Not a secret, and not a key this package
  ever holds.
- **Delivery**: how the provider's library reaches the browser. The project's decision, made
  however it already manages its frontend. Not this package's to make or to emit.
- **Checkout**: the provider-hosted flow the pricing table sends a person into. Reached from here,
  never reproduced here, and never seen by this package.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A project that installs this package beside the backend, mounts its URLs and supplies
  a pricing table identifier and publishable key gets a working plan-choosing page, having written
  no view and no template.
- **SC-002**: The rendered output of every page and placement in this feature contains no script
  element referencing the provider.
- **SC-003**: A subscription bought through the shipped page by a signed-in person is attached to
  that person's account, with no manual reconciliation.
- **SC-004**: The same component renders correctly both inside the Account Center and in an
  unrelated template placed by the project, including for a reader who is not signed in.
- **SC-005**: A project with no pricing table identifier configured gets a page that says so, with
  nothing raised and no empty region where the table would be.
- **SC-006**: A project replaces the component with its own markup and the shipped page renders it,
  with no other change to the project.
- **SC-007**: No figure about price appears anywhere in this package's own output.
- **SC-008**: A current subscriber can reach no path in this package's pages that ends in a second
  subscription beside the one they have.

## Assumptions

- The backend in question is drf-stripe-subscription, the namespace this package ships today. A
  second backend gets its own namespace and its own embed component.
- The project has created a pricing table in the provider's dashboard. What it contains, how it is
  styled and where a buyer is sent afterwards are all configured there, and none of them is this
  package's to influence.
- The project loads the provider's pricing table library itself. The demonstration project does it
  with a tag pointing at the provider's own network, labelled as a demonstration convenience rather
  than a recommendation.
- The backend matches a provider customer to an application user by email address and reads no
  other identifier. This is the backend's behaviour, confirmed in its source, and the reason FR-005
  exists. A project that has configured the backend to create users will get one created for an
  unrecognised address, which is the backend's decision and not this page's.
- The Plans page, its navigation entry and its card were delivered by an earlier feature. Nothing
  here changes how a page arrives, only what is on one of them.
- This package holds no state, computes nothing about money and reaches no provider from the
  server. Those are standing constraints rather than choices this feature makes. Rendering an
  embed's mount point is explicitly allowed by them: the card is typed into the provider's own
  frame, which is what an embed is for.
- A standing rule in this repository currently says a publishable key is never read from the
  project's settings anywhere in this package. FR-004 narrows it to the component, and the
  reasoning is recorded in `decisions.md`. The rule's text is amended by the work that implements
  this spec.
