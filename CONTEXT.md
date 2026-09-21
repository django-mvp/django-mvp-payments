# django-mvp-payments

Domain model for django-mvp-payments — payment and subscription UI as Cotton components for
projects built on django-mvp.

The terms below are the ones to use in issues, commits, tests and component names. Several exist
to keep three vocabularies apart that are easy to collapse into one: the payment company, the
Django package that talks to it, and the thing a customer sees. English reuses the same words for
all three, and a bug report that mixes them cannot be acted on.

## Core concepts

**Payment component**:
The unit this package ships: one Cotton component rendering one piece of payment or subscription
interface, configured entirely through its attributes. `<c-drf-stripe.plan-grid>` is a payment
component.
_Avoid_: widget, block, element, partial.

**Provider**:
The payment company whose money rails are used — Stripe, PayPal, Paddle. A provider hosts pages of
its own and publishes its own browser script.
_Avoid_: gateway, processor, vendor.

**Backend**:
The Django package that talks to a provider, holds whatever local state it keeps and exposes it to
the application. drf-stripe-subscription is the first backend. A backend is chosen by the template
author per component, by picking a namespace, and is never swapped by configuration.
_Avoid_: integration (this package integrates with nothing — the backend does), adapter, driver,
provider (that is the company, above).

**Contribution**:
Everything one namespace puts into the Account Center when its backend is installed — its
navigation entries, its overview card and its pages. Made or not made as a whole, on one
condition, so the three cannot drift apart from one another.
_Avoid_: integration (see Backend, above), registration (the mechanism that adds a contribution,
not the contribution itself).

**Namespace**:
The first segment of a component tag, naming the backend: `drf-stripe` in
`<c-drf-stripe.plan-grid>`. Cotton resolves it to a directory, so
`mvp_payments/templates/cotton/drf_stripe/`. The namespace is the backend rather than this
package, which is what allows a second backend to be added alongside the first without touching
it.
_Avoid_: prefix, module, family.

**Plan**:
What a customer chooses — a named thing at a price, on a billing frequency. It is a presentation
term, and deliberately not a data term: no backend has a `Plan` record, and Stripe retired the
word in favour of prices. `plan-grid` and `plan-card` are named for what a person is looking at.
The records behind them are the backend's, named in the backend's own words.
_Avoid_: tier, package (means this distribution), SKU, product (which is a specific record in some
backends and must keep that meaning).

**Subscription**:
The backend's record that a host project's user is signed up to something, with a status and a
period. This package displays it and never creates, changes or cancels one.
_Avoid_: membership, plan (above), licence, entitlement.

**Checkout**:
The provider-hosted flow that takes payment. A component starts it and the customer completes it
off-site, then returns. No card details ever pass through this package or the host project.
_Avoid_: purchase, cart, payment form, payment flow.

**Billing portal**:
The provider-hosted page where a customer changes payment method, reads invoices and cancels. Like
checkout, a component sends them there rather than reproducing it.
_Avoid_: billing page, account centre, customer centre.

**Host project**:
The Django project that installs this package. It owns the theme, the base template, the URLs,
who is allowed to see what, and how a provider's script reaches the browser.
_Avoid_: consumer, client, downstream, user (a user is a person, not a project).

**Theme**:
A daisyUI theme, supplied by django-mvp and selected by the host project. Components render
semantic classes rather than literal colours, so a pricing page follows the site when the theme
changes.
_Avoid_: skin, palette, colour scheme.

**Delivery**:
How a provider's JavaScript reaches the browser. It is the host project's decision, made however
that project already manages its frontend — a CDN tag, a bundler entry point, an import map. This
package emits no script tag for a provider's library, and the demo project's CDN tag is a
demonstration convenience rather than a recommendation.
_Avoid_: bundling (names only one of the answers), asset pipeline, static files.

## Terms deliberately not used

**Agnostic**: read as "a component works across backends", which is the opposite of the design.
Say which backend, or say *per-backend namespace*.

**Paywall**: names an access-control decision — who may see what, and what happens when they may
not. That is the host project's, enforced in its views. Using the word here invites requests for
permission logic this package will not have.

**Billing**: too broad to mean anything on its own; it covers the provider's invoicing, the
backend's records and the pages a customer reads. Name which one.

**Payment method**: only ever a provider's stored instrument. This package never collects, stores
or displays card details, so the term should appear here only when describing what happens
somewhere else.
