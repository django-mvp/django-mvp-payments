# django-mvp-payments

Domain model for django-mvp-payments — payment and subscription UI as Cotton components for
projects built on django-mvp, and the provider apps that keep the records behind it.

The terms below are the ones to use in issues, commits, tests and component names. Several exist
to keep three vocabularies apart that are easy to collapse into one: the payment company, the
code that talks to it, and the thing a customer sees. English reuses the same words for
all three, and a bug report that mixes them cannot be acted on.

## Core concepts

**Payment component**:
The unit this package ships: one Cotton component rendering one piece of payment or subscription
interface, configured entirely through its attributes. `<c-stripe.plan-card>` is a payment
component.
_Avoid_: widget, block, element, partial.

**Provider**:
The payment company whose money rails are used — Stripe, PayPal, Paddle. A provider hosts pages of
its own and publishes its own browser script.
_Avoid_: gateway, processor, vendor.

**Backend**:
The code that talks to a provider and keeps the local records a page reads. In this package a
backend is a provider app, and `mvp_payments.stripe` is the first. A backend is chosen by the template author per component, by picking a namespace, and is never
swapped by configuration.
_Avoid_: integration, adapter, driver, provider (that is the company, above).

**Provider app**:
An app inside this package that talks to one provider: it keeps the local copy of that
provider's customers and subscriptions, receives its webhooks and hands readers to its hosted
pages. A project turns one on by adding it to `INSTALLED_APPS`. `mvp_payments.stripe` is the
Stripe app.
_Avoid_: plugin, extension, integration, sub-package.

**Webhook**:
The provider's notice that something about a customer or subscription has changed, sent to an
endpoint a provider app mounts. Its signature is checked, and it is then a prompt to ask the
provider for the current state, never the state itself.
_Avoid_: callback, hook, event (an event is the provider's object that a webhook carries).

**stripe-lite**:
The name of the install option, `django-mvp-payments[stripe-lite]`, that brings in what the Stripe
app needs. It names that extra and nothing else: the app is the Stripe app, `mvp_payments.stripe`.
The name says the app is deliberately small, so that nobody reads it as support for a fuller
Stripe integration such as dj-stripe.
_Avoid_: using it for the app, the namespace or the provider.

**Contribution**:
Everything one namespace puts into the Account Center when its backend is installed — its
navigation entries, its overview card and its pages. Made or not made as a whole, on one
condition, so the three cannot drift apart from one another.
_Avoid_: integration (see Backend, above), registration (the mechanism that adds a contribution,
not the contribution itself).

**Namespace**:
The first segment of a component tag, naming the backend: `stripe` in
`<c-stripe.plan-card>`. Cotton resolves it to a directory, so
`mvp_payments/templates/cotton/stripe/`. The namespace is the backend rather than this
package, which is what allows a second backend to be added alongside the first without touching
it.
_Avoid_: prefix, module, family.

**Plan**:
What a customer chooses — a named thing at a price, on a billing frequency. It is a presentation
term, and deliberately not a data term: no backend has a `Plan` record, and Stripe retired the
word in favour of prices. The user subscriptions page shows a plan because that is what a person is
looking at. The record behind it is the backend's, named in the backend's own words.
_Avoid_: tier, package (means this distribution), SKU, product (which is a specific record in some
backends and must keep that meaning).

**Subscription**:
The record that a host project's user is signed up to something, with a status and a period.
A provider app records it as the provider reports it. Nothing in this package creates, changes or
cancels one: that happens on the provider's hosted pages.
_Avoid_: membership, plan (above), licence, entitlement.

**Checkout**:
The provider-hosted flow that takes payment. A component starts it and the customer completes it
off-site, then returns. No card details ever pass through this package or the host project.
_Avoid_: purchase, cart, payment form, payment flow.

**Billing portal**:
The provider-hosted page where a customer changes payment method, reads invoices and cancels. Like
checkout, a component sends them there rather than reproducing it.
_Avoid_: billing page, account centre, customer centre.

**Plans page**:
The page showing every plan on offer, drawn from the prices in the Stripe account. Anyone can open
it, signed in or not, whatever they are already subscribed to. It has an address of its own,
outside the Account Center, which the host project chooses.
_Avoid_: pricing page, subscribe page, upgrade page.

**User subscriptions page**:
The page showing a signed-in person the subscriptions they hold, each with its status, and the
way through to Stripe's portal. Only that person's own subscriptions, and only when signed in.
_Avoid_: subscription page, billing page, account page, my plan.

**Billing**:
The Account Center section this package's pages sit under, and nothing else. It is a navigation
category, where breadth is the point: a reader looking for anything to do with what they pay finds
it under one heading, and invoices or payment methods have somewhere obvious to arrive later. In
running prose it still says too little to be useful on its own, so name the specific thing — the
billing portal, the subscription, the provider's invoices.
_Avoid_: using it for a page, a record or an amount.

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
package emits no script tag for a provider's library.
_Avoid_: bundling (names only one of the answers), asset pipeline, static files.

## Terms deliberately not used

**Agnostic**: read as "a component works across backends", which is the opposite of the design.
Say which backend, or say *per-backend namespace*.

**Paywall**: names an access-control decision — who may see what, and what happens when they may
not. That is the host project's, enforced in its views. A provider app can tell a project whether
someone is subscribed, and what that grants stays the project's decision. Using the word here
invites requests for permission logic this package will not have.

**Payment method**: only ever a provider's stored instrument. This package never collects, stores
or displays card details, so the term should appear here only when describing what happens
somewhere else.
