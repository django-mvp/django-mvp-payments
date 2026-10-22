# The plans page

The `stripe` namespace contributes a page offering every visitor the plans they can choose from.
It arrives with the package: add `mvp_payments.stripe` to `INSTALLED_APPS`, mount this package's
URLs once, and the page is routed and reached from the user subscriptions page. There is no view to
write. It has no entry in the Account Center's navigation, so it is drawn with the project's own
sidebar.

The page is open to everyone. A visitor who is not signed in sees it, a signed-in person sees it,
and a person who already has a subscription sees it, with the same pricing table. Signing in
changes what the table is given, not whether it is shown.

Unlike the user subscriptions page, this page shows nothing of the Stripe app's own records. It mounts
the provider's own embeddable pricing table — [Stripe's pricing
table](https://docs.stripe.com/payments/checkout/pricing-table) — and reads two settings to
configure it. No amount, currency, billing frequency or plan name is produced anywhere by this
package; the provider renders every price inside its own frame.

## The component

`<c-stripe.pricing-table>` emits the provider's `<stripe-pricing-table>` custom element.

```html
<c-stripe.pricing-table :table_id="pricing_table_id" :publishable_key="publishable_key" />
```

It declares five attributes:

| Attribute | What it does |
|---|---|
| `table_id` | Carried into the element's `pricing-table-id` attribute. Required. |
| `publishable_key` | Carried into the element's `publishable-key` attribute. Required — and not a secret: it identifies the account, and the provider prints it in its own copy-paste examples. |
| `client_reference_id` | Carried into the element's `client-reference-id` attribute when there is one. Optional. |
| `customer_session_client_secret` | Carried into the element's `customer-session-client-secret` attribute when there is one. Optional. |
| `customer_email` | Carried into the element's `customer-email` attribute when there is an address to carry and no customer session. Optional. |

The component reads no settings and imposes no sign-in requirement, so it can be placed on any
page of your own project, whether or not this package's Account Center pages are in use.

### What ties a purchase to a person

Stripe's checkout is hosted by Stripe, so the package never sees it. What makes the subscription
that results belong to a user is a reference that goes out with the pricing table and comes back
on the completed checkout, where the Stripe app's webhook checks it
([ADR 0011](../adr/0011-a-checkout-is-tied-to-its-user-by-a-signed-reference.md)).

The plans page passes the pricing table two things for a signed-in person:

- **`client-reference-id`** is `Customer.client_reference(request.user)`: the person's primary key
  and a signature of it. The signature stops anyone embedding your public pricing table with
  someone else's key.
- **`customer-session-client-secret`** is passed when the person already has a Stripe customer. The
  Stripe app creates a customer session for that customer on the server, so a second purchase
  lands on the customer they have instead of creating another. If Stripe cannot be asked, the
  page logs the kind of error, leaves the session out, and shows the table anyway. The reference
  still ties the purchase to them.

For a person with no Stripe customer yet, the page passes no session, and the component passes the
address on their account, if they have one, as `customer-email`, so Stripe can prefill it. An
address supplied as the `customer_email` attribute wins over the account's. The provider accepts a
customer session or an email address, not both, so the component omits the address whenever a
session is passed. Where there is no address, the attribute is omitted rather than emitted empty.

```html
<c-stripe.pricing-table :table_id="pricing_table_id"
                        :publishable_key="publishable_key"
                        :client_reference_id="client_reference_id"
                        :customer_session_client_secret="customer_session_client_secret" />
```

A visitor who is not signed in gets none of these. A purchase made then is tied to nobody: the
Stripe app's webhook finds no reference to verify and records nothing, and the package does not
try to match the buyer by email. The page says so before it happens (see below).

## The page

`PlansPageView` adds five names to the template context. The first two are read from your
settings at render time:

`pricing_table_id`
: `MVP_PAYMENTS["STRIPE_PRICING_TABLE_ID"]` — the pricing table's id, from the provider's
  dashboard. `None` when the setting is absent.

`publishable_key`
: `MVP_PAYMENTS["STRIPE_PUBLISHABLE_KEY"]` — the account's publishable key. `None` when the
  setting is absent.

`client_reference_id`
: The signed reference for the signed-in person. `None` for a visitor who is not signed in.

`customer_session_client_secret`
: The secret of a customer session for the signed-in person's Stripe customer. `None` when they
  have none, when Stripe could not be asked, and for a visitor who is not signed in.

`sign_in_url`
: For a visitor who is not signed in, the project's sign-in page with `next` set to the plans
  page, so signing in brings them back. `None` for a signed-in person.

```python
MVP_PAYMENTS = {
    "STRIPE_PRICING_TABLE_ID": "prctbl_...",
    "STRIPE_PUBLISHABLE_KEY": "pk_...",
}
```

The shipped page renders the component when both values are present, and a plain sentence in
their place when either is absent. Above the component, a visitor who is not signed in gets
`<c-stripe.sign-in-notice>`, which says to sign in before choosing a plan and links to
`sign_in_url`. It takes one attribute, `url`, and renders nothing without it.

Where a buyer goes after paying is set on the pricing table in the provider's dashboard. Send them
to the user subscriptions page with `?returned=1` on the address, so the page waits for the payment to
reach the Stripe app instead of telling them they have no subscription. See
[Coming back from the provider](user-subscriptions-page.md#coming-back-from-the-provider).

```html
{% extends "mvp/account/base.html" %}
{% block account.content %}
  <c-mvp.page>
    <c-mvp.page.title :title="page.title" />
    {% if pricing_table_id and publishable_key %}
      <c-stripe.sign-in-notice :url="sign_in_url" />
      <c-stripe.pricing-table :table_id="pricing_table_id"
                              :publishable_key="publishable_key"
                              :client_reference_id="client_reference_id"
                              :customer_session_client_secret="customer_session_client_secret" />
    {% else %}
      <c-stripe.plans-unavailable />
    {% endif %}
  </c-mvp.page>
{% endblock account.content %}
```

The page extends `mvp/account/base.html`, which draws the project's own base layout and does not
need a signed-in person.

## Before it is configured

A project that has not yet supplied `STRIPE_PRICING_TABLE_ID`, `STRIPE_PUBLISHABLE_KEY`, or
`MVP_PAYMENTS` at all, gets a page that says plans are not available — never an empty region
with nothing to explain it. `<c-stripe.plans-unavailable>` renders that sentence and takes no
props of its own.

## Loading the provider's library

The element renders as nothing until `https://js.stripe.com/v3/pricing-table.js` has loaded.
Self-hosting that library is forbidden by the provider's own terms, so it has to come from the
provider's own network — and loading it is your project's decision, not this package's. This
package emits no `<script>` tag for it anywhere, which
`tests.test_app.TestNoProviderScript` holds as a guarantee across every template it ships.

Load it the way you already load your project's other frontend assets — a CDN tag, a bundler
entry point, an import map, whatever your project already uses:

```html
<script defer src="https://js.stripe.com/v3/pricing-table.js"></script>
```

The demo project does this in `demo/templates/base.html`, inside a `{% block provider_library %}`
labelled a demonstration convenience rather than a recommendation.

## When the library never arrives

Loading the provider's library is your project's decision, and there is no guarantee it always
succeeds — the project may not have loaded it at all, or a reader's browser could not reach the
provider's origin. Either way the element renders as nothing, with no event to signal it.

The component carries a message for exactly this, rendered hidden in the same markup as the
element rather than injected by JavaScript — the message is translatable this way, and revealing
it needs no string in a `.js` file (`FR-010`).

`mvp_payments/static/mvp_payments/stripe/pricing_table.js` is what reveals it: after your
page's `load` event, it checks `customElements.get("stripe-pricing-table")`. Undefined means the
library never arrived, and the hidden message is shown. Load this file the way you load the
provider's own library — it emits no message of its own and fetches nothing:

```html
<script defer src="{% static 'mvp_payments/stripe/pricing_table.js' %}"></script>
```

## Replacing the component or the page

Two different things can be replaced, and what each keeps differs.

### Replacing the component

Supply your own `cotton/stripe/pricing_table.html`, earlier on the template search path than
this package, and every `<c-stripe.pricing-table>` tag renders it instead — no view and no
query of your own is needed. The shipped page still calls the component with the same
attributes, so this changes only what the tag itself renders; the page's URL, its
context and its unavailable-state branch all stay the shipped page's.

### Replacing the page

Supply your own template at `mvp_payments/stripe/plans.html`, earlier on the template search
path than this package, and it is used instead — no view, no context processor and no query of
your own is needed, and every name listed above is already in the context. This replaces
everything the template decides, including whether to use the component at all; only the view
underneath it — the URL, the page being open to everyone, and the names it puts in the context —
stays the shipped page's.

Django's app-directories template loader checks `INSTALLED_APPS` in order and uses the first
match it finds, so your own application needs to appear before `mvp_payments` in that list for its
copy to be found first — the same mechanism that requires this package itself to precede `mvp`
(see the README's Install step).
