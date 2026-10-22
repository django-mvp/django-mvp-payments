# Feature Specification: Keep each user's Stripe subscription in the project's own database

**Feature Branch**: `004-stripe-app`

**Created**: 2026-10-21

**Status**: Draft

**Serves**: G2 (at least one payment provider is supported, with the records behind its pages kept by this package)

**Roadmap**: R2 — The first backend: the package's own Stripe app

**Issue**: #52

**Input**: A Stripe app inside this package, `mvp_payments.stripe`, installed with the
`stripe-lite` extra and turned on by adding it to `INSTALLED_APPS`. It keeps each user's Stripe
customer and subscription in the project's own database, kept in step with Stripe through
Stripe's webhooks, with no Django REST Framework and no third-party Stripe integration. A
developer can ask in their own views whether a user is subscribed, re-sync from Stripe after
webhooks were missed, and see who is subscribed to what in the admin. The demo receives
Stripe's webhooks locally. Products and prices are not copied. Taxes, invoices, metered billing,
one-off payments and billing for teams are out of scope. Moving the existing subscription and
plans pages onto the app is separate work that follows this feature.

## Clarifications

### Session 2026-10-21

The coverage scan found five ambiguities. Each was answered from the intake discussion, the
constitution as amended on 2026-10-20 and Stripe's published behaviour. Longer rationale is in
`decisions.md`.

- **Q: A person buys on Stripe's hosted checkout, which the app never sees. What makes the
  subscription theirs?**
  A: The identity of the signed-in person, carried through checkout by Stripe and returned with
  the completed checkout. Matching on email address alone attaches a purchase to nobody when the
  person types a different address at checkout. A Stripe customer
  the app cannot tie to a user is not recorded against anyone. Recorded as FR-006 and FR-007.

- **Q: Stripe allows a customer more than one subscription. Does the app keep one per user or
  all of them?**
  A: All of them, as Stripe reports them. A person normally has one, but a second can be bought
  separately, and a record that kept only one would hide it. Whether a
  user is subscribed is answered from all of their subscriptions. Recorded as FR-004 and FR-012.

- **Q: Which statuses count as "subscribed"?**
  A: Active and trialing, which includes a subscription that has been cancelled but has not yet
  reached the end of its period. Past due, unpaid, incomplete, paused and ended do not. This is
  the common reading of Stripe's statuses and one a project can rely on without thinking. A
  project that needs a different reading reads the stored status itself. Recorded as FR-012.

- **Q: What happens when a subscription or customer is deleted on Stripe's side?**
  A: The app records what Stripe now says. An ended subscription keeps its record with its ended
  status, so the history stays visible in the admin. A deleted customer leaves the user with no
  current subscription, and the user is never shown or reported as subscribed from a record Stripe
  no longer has. Recorded as FR-009.

- **Q: How does the demo receive webhooks without a public address?**
  A: Through Stripe's own command-line tool, which forwards a sandbox account's events to the
  local server. The demo documents the one command and the setting it prints. Without it the demo
  still runs, and nothing is kept in step. Recorded as FR-016.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A developer keeps their users' subscriptions in step with Stripe (Priority: P1)

A developer installs `django-mvp-payments[stripe-lite]`, adds `mvp_payments.stripe` to
`INSTALLED_APPS`, puts their Stripe secret key and webhook signing secret in their settings, runs
the migrations, mounts the package's URLs and points Stripe's webhooks at the address the app
provides. When one of their users subscribes on Stripe's checkout, the user's Stripe customer and
subscription appear in the project's database. When the user switches plan, cancels, or a payment
fails, the record changes to match.

**Why this priority**: It is the feature. Every other story reads the records this one keeps.

**Independent Test**: With the app installed, send the app a signed webhook for a subscription
created through checkout by a known user, and confirm that user's customer and subscription are
recorded with the status, price and period Stripe holds. Send one for a change and confirm the
record follows.

**Acceptance Scenarios**:

1. **Given** the app is installed and configured, **When** a signed-in user completes Stripe's
   checkout and Stripe reports it, **Then** the user's Stripe customer and subscription are
   recorded against that user, with the status, price, billing frequency, amount, currency and
   current period Stripe holds.
2. **Given** a recorded subscription, **When** Stripe reports a change to it (a plan switch, a
   cancellation at period end, a failed payment, its end), **Then** the record matches what Stripe
   holds for that subscription after the change.
3. **Given** a request to the webhook address whose signature does not verify, **When** it arrives,
   **Then** it is refused and no record changes.
4. **Given** a verified event, **When** it arrives twice, late, or after a newer event about the same
   subscription, **Then** the record ends up matching what Stripe currently holds, and no duplicate
   is created.
5. **Given** a verified event about a type of object the app does not keep, **When** it arrives,
   **Then** it is acknowledged and no record changes.
6. **Given** the app is installed but its secret key or webhook signing secret is missing, **When**
   the project runs its system checks, **Then** the developer is told which is missing.

---

### User Story 2 - A developer checks whether a user is subscribed (Priority: P1)

A developer writing a view of their own asks the app whether the signed-in user is subscribed,
and decides for themselves what that lets the user see.

**Why this priority**: Showing a subscription is half the reason a project keeps one. The other
half is acting on it, and without a supported way to ask, every project writes the same query
against the app's records and gets the statuses subtly wrong.

**Independent Test**: Create users with subscriptions in each status Stripe reports, and with
none, and ask for each. The answer is yes for exactly the statuses that count as subscribed.

**Acceptance Scenarios**:

1. **Given** a user with an active or trialing subscription, including one set to cancel at the end
   of its period, **When** a developer asks whether they are subscribed, **Then** the answer is yes.
2. **Given** a user whose only subscriptions are past due, unpaid, incomplete, paused or ended, or
   who has none, or who is not signed in, **When** asked, **Then** the answer is no.
3. **Given** a user with more than one subscription, **When** asked, **Then** the answer is yes if any
   one of them counts as subscribed.
4. **Given** a developer who needs the subscription itself rather than a yes or no, **When** they ask
   for a user's current subscription, **Then** they get it, with its status, price and period, or
   nothing when the user has none that counts.

---

### User Story 3 - A developer re-syncs from Stripe after missed webhooks (Priority: P2)

A developer whose webhook address was down, misconfigured or not yet set up runs one management
command, and every recorded customer's subscriptions are brought back into step with Stripe.

**Why this priority**: Webhooks are missed in practice: a deploy, an expired secret, an address
changed in one place and not the other. Without a way to catch up, the only fix is editing
records by hand, which the constitution forbids.

**Independent Test**: Record a subscription, change it on Stripe without sending the webhook, run
the command, and confirm the record matches Stripe.

**Acceptance Scenarios**:

1. **Given** recorded customers whose subscriptions changed on Stripe while no webhooks arrived,
   **When** the developer runs the sync command, **Then** every one of their subscriptions matches
   what Stripe holds.
2. **Given** a recorded customer that Stripe no longer has, **When** the command runs, **Then** that
   user is left with no current subscription.
3. **Given** the command is run twice in a row, **When** the second run finishes, **Then** nothing has
   changed between the two.
4. **Given** the developer names one user, **When** the command runs, **Then** only that user's
   records are synced.
5. **Given** Stripe cannot be reached partway through, **When** the command stops, **Then** it says so,
   the records already synced are kept, and running it again finishes the rest.

---

### User Story 4 - Staff see who is subscribed to what in the admin (Priority: P2)

Someone with access to the project's Django admin looks up a user and sees their Stripe customer
and subscriptions, with each one's status, price and period, and can find all users in a given
status.

**Why this priority**: The first support question any subscription site gets is "why can't I see
this, I've paid". Answering it should not need a database shell.

**Independent Test**: Open the admin as a staff user with view permission and find a user's
subscription by their username or email address, then list every subscription in a given status.

**Acceptance Scenarios**:

1. **Given** recorded subscriptions, **When** a staff user with view permission opens the admin,
   **Then** they can list subscriptions, filter them by status and search them by the user's
   username or email address.
2. **Given** a subscription in the admin, **When** a staff user opens it, **Then** they see its user,
   its Stripe identifiers, status, price, amount with its currency, and period.
3. **Given** any staff user, including a superuser, **When** they open a customer or subscription in
   the admin, **Then** nothing in it can be added, changed or deleted.

---

### User Story 5 - A developer running the demo receives Stripe's webhooks locally (Priority: P3)

A developer working on this package, or trying it out, runs the demo against a Stripe sandbox and
forwards that sandbox's webhooks to the local server with one documented command. Subscribing,
switching plans and cancelling in the sandbox then shows up in the demo's records.

**Why this priority**: Without it the webhook path is never exercised outside the tests, and the
demo keeps needing a workaround to stay in step.

**Independent Test**: Follow the demo's documented steps with a sandbox account, subscribe a demo
user, and confirm the subscription is recorded.

**Acceptance Scenarios**:

1. **Given** a sandbox account's keys in the demo's local settings and the forwarding command
   running, **When** a demo user subscribes in the sandbox, **Then** the demo records their
   subscription.
2. **Given** the forwarding command is not running, **When** the demo starts, **Then** it still runs.

---

### Edge Cases

- A webhook arrives for a customer who was never tied to a user: acknowledged, nothing recorded.
- A user who already has a Stripe customer subscribes again: the same customer is reused and the
  new subscription is recorded beside the old one.
- The user a customer is tied to is deleted from the project: the customer and its subscriptions
  go with them. Nothing is changed on Stripe.
- Stripe reports a status the app does not recognise: it is stored as reported and does not count
  as subscribed.
- An amount in a zero-decimal currency such as JPY: stored exactly as Stripe reports it, in the
  minor unit, with its currency.
- Stripe is unreachable when a verified webhook arrives: the webhook is answered with a failure so
  that Stripe retries it, and no record changes.
- The webhook signing secret is rotated: a webhook signed with the old secret is refused once the
  setting changes.
- The extra is installed but `mvp_payments.stripe` is not in `INSTALLED_APPS`: nothing is mounted,
  migrated or contributed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST ship an app, `mvp_payments.stripe`, that a project turns on by adding
  it to `INSTALLED_APPS`. Its dependencies MUST be installed only through the package's
  `stripe-lite` extra, and nothing outside the app MUST import them.
- **FR-002**: The app MUST NOT require Django REST Framework, pydantic, or any third-party Stripe
  integration.
- **FR-003**: The app MUST record, for each user who becomes a Stripe customer, that user's Stripe
  customer identifier.
- **FR-004**: The app MUST record every subscription Stripe reports for a recorded customer, with
  its Stripe identifier, status, price identifier, product name, amount in the currency's minor
  unit, currency, billing interval and interval count, current period start and end, whether it
  cancels at the end of the period, and when it ended.
- **FR-005**: The app MUST provide a webhook address, mounted with the package's URLs, that
  verifies each request's signature against the configured signing secret before reading anything
  else in it, and refuses a request that does not verify.
- **FR-006**: On a verified event about a checkout, customer or subscription, the app MUST fetch
  the current state of the affected subscriptions from Stripe and record that, rather than the
  contents of the event, so that repeated, late and out-of-order events leave the same records.
- **FR-007**: A Stripe customer MUST be tied to a user only through the identity of the signed-in
  user carried through Stripe's checkout, or through a customer the app itself recorded for that
  user. A customer that cannot be tied to a user MUST NOT be recorded against anyone.
- **FR-008**: Records MUST change only from what Stripe reports, through a webhook, the sync
  command, or a fetch the app makes. Nothing in the app MUST let a person add, change or delete a
  record directly.
- **FR-009**: Where Stripe reports a subscription as ended, the app MUST keep its record with that
  status. Where Stripe no longer has a recorded customer, the app MUST leave that user with no
  current subscription.
- **FR-010**: A verified event about an object the app does not keep MUST be acknowledged and
  change nothing. A verified event that cannot be processed because Stripe could not be reached
  MUST be answered with a failure, so that Stripe sends it again.
- **FR-011**: The app MUST state the Stripe API version it is written against and use it for every
  call it makes, rather than relying on the account's default.
- **FR-012**: The app MUST provide a documented way for a developer to ask whether a user is
  subscribed, answering yes when any of the user's subscriptions is active or trialing, and no
  otherwise, including for anonymous users.
- **FR-013**: The app MUST provide a documented way for a developer to get a user's current
  subscription.
- **FR-014**: The app MUST provide a management command that brings every recorded customer's
  subscriptions back into step with Stripe, or one named user's, which is safe to run repeatedly
  and keeps what it has synced if it stops partway.
- **FR-015**: The app MUST register its customers and subscriptions in the Django admin as
  read-only for every user, searchable by the user's username and email address and filterable by
  status.
- **FR-016**: The demo MUST document how to forward a Stripe sandbox's webhooks to the local
  server, and MUST run without it.
- **FR-017**: The app MUST tell a developer, through Django's system checks, when its secret key or
  webhook signing secret is not configured.
- **FR-018**: The secret key and webhook signing secret MUST be read only from the project's
  settings, and MUST NOT appear in a template, a template context, a log message, an error page or
  a fixture.
- **FR-019**: The app MUST NOT copy Stripe's products, prices, invoices or payment methods, and
  MUST NOT compute any price, proration or trial.
- **FR-020**: The app's models MUST ship with migrations, and its tables MUST carry the
  `mvp_payments_stripe` label.
- **FR-021**: The app's settings, its webhook address, the subscribed check, the current
  subscription lookup, the sync command and the admin MUST be documented, and the README's install
  steps MUST describe the `stripe-lite` extra and the `INSTALLED_APPS` entry.

### Key Entities

- **Customer**: a user's Stripe customer. One per user at most. Holds the user and the Stripe
  customer identifier.
- **Subscription**: one Stripe subscription belonging to a customer. Holds its Stripe identifier,
  status, the price it is on and that price's product name, amount, currency and billing interval,
  the current period, whether it cancels at period end, and when it ended. A customer may have
  several.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer goes from a project without the app to recorded subscriptions by
  following the install, `INSTALLED_APPS`, settings, migrate, URL and webhook steps in the
  documentation, with no code of their own.
- **SC-002**: For every subscription status Stripe documents, the recorded status and the
  subscribed answer are correct, proven by tests.
- **SC-003**: Every event the app handles, delivered twice, late, or out of order, leaves the same
  records as delivering it once in order, proven by tests.
- **SC-004**: A request with a missing, wrong or expired signature changes no record, proven by
  tests.
- **SC-005**: Installing the package without the extra installs no Stripe library, and nothing
  outside `mvp_payments.stripe` imports one, both asserted by the test suite.
- **SC-006**: The sync command run against changed Stripe data leaves the records matching Stripe,
  and a second run changes nothing.
- **SC-007**: No staff user, superusers included, can add, change or delete a customer or
  subscription in the admin.
- **SC-008**: The secret key and webhook signing secret appear in no rendered page, log line or
  error response, asserted by tests.

## Assumptions

- A person normally has one subscription, and may hold several. Switching plans, cancelling and
  updating payment details all happen on Stripe's hosted pages.
- Every checkout the app starts carries the signed-in user's identity, and the
  subscription and plans pages, the portal and plan-change handoffs and the return from Stripe all
  run on this app.
- Nothing is migrated from the backend the first pages were built on, because nothing has been
  released.
- Trials appear only as a status. Taxes, invoices, metered billing, one-off payments, coupons
  beyond Stripe's hosted pages, and billing for teams or organisations are out of scope.
- Stripe is the source of truth. Where the app's records and Stripe disagree, Stripe is right.
