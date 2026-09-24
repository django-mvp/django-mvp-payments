# The plans page

The `drf-stripe` namespace contributes a page offering a signed-in person the plans they can choose
from. It arrives with the package: install this alongside
[drf-stripe-subscription](https://github.com/oscarychen/drf-stripe-subscription), mount this
package's URLs once, and the page is in the Account Center's navigation. There is no view to write.

Unlike the subscription page, this page shows nothing of the backend's own records. It mounts the
provider's own embeddable pricing table — [Stripe's pricing
table](https://docs.stripe.com/payments/checkout/pricing-table) — and reads two settings to
configure it. No amount, currency, billing frequency or plan name is produced anywhere by this
package; the provider renders every price inside its own frame.

## The component

`<c-drf-stripe.pricing-table>` emits the provider's `<stripe-pricing-table>` custom element.

```html
<c-drf-stripe.pricing-table :table_id="pricing_table_id" :publishable_key="publishable_key" />
```

It declares three attributes:

| Attribute | What it does |
|---|---|
| `table_id` | Carried into the element's `pricing-table-id` attribute. Required. |
| `publishable_key` | Carried into the element's `publishable-key` attribute. Required — and not a secret: it identifies the account, and the provider prints it in its own copy-paste examples. |
| `customer_email` | Carried into the element's `customer-email` attribute when there is an address to carry. Optional — see below for where it comes from. |

The component reads no settings and imposes no sign-in requirement, so it can be placed on any
page of your own project, whether or not this package's Account Center pages are in use.

### Where the address comes from

The installed backend matches a provider customer to an application user by email address alone.
A purchase made under a different address than the signed-in person's own attaches to nobody, so
the component passes one wherever it can.

An address supplied as the `customer_email` attribute wins. Otherwise the component reads
`request.user` from the context and uses that person's address when they are signed in and hold
one. Where there is neither — an anonymous visitor, or a signed-in person whose account carries no
address — the `customer-email` attribute is omitted entirely rather than emitted empty: an empty
`customer-email` is not the same instruction to the provider as an absent one.

```html
<c-drf-stripe.pricing-table :table_id="pricing_table_id"
                             :publishable_key="publishable_key"
                             customer_email="someone@example.com" />
```

## The page

`PlansPageView` adds four names to the template context. The first two are read from your
settings at render time:

`pricing_table_id`
: `MVP_PAYMENTS["DRF_STRIPE_PRICING_TABLE_ID"]` — the pricing table's id, from the provider's
  dashboard. `None` when the setting is absent.

`publishable_key`
: `MVP_PAYMENTS["DRF_STRIPE_PUBLISHABLE_KEY"]` — the account's publishable key. `None` when the
  setting is absent.

`subscriptions`
: The person's current subscriptions, as the subscription page reads them.

`subscription_url`
: Where the subscription page is mounted.

```python
MVP_PAYMENTS = {
    "DRF_STRIPE_PRICING_TABLE_ID": "prctbl_...",
    "DRF_STRIPE_PUBLISHABLE_KEY": "pk_...",
}
```

The shipped page renders the component when both values are present, and a plain sentence in
their place when either is absent. Somebody who already has a subscription gets neither. They see
`<c-drf-stripe.already-subscribed>` instead, which says they already have one and links to their
subscription page. The pricing table cannot show which plan they are on, and buying from it starts
a second subscription beside the first. Changing plan happens on the provider's plan-change screen,
reached from the subscription page's "Switch plans" control. It keeps `LoginRequiredMixin`, so an anonymous visitor is sent
to sign in rather than shown the page.

```html
{% extends "mvp/account/base.html" %}
{% block account.content %}
  <c-page>
    <c-page.title :title="page.title" />
    {% if subscriptions %}
      <c-drf-stripe.already-subscribed :url="subscription_url" />
    {% elif pricing_table_id and publishable_key %}
      <c-drf-stripe.pricing-table :table_id="pricing_table_id"
                                   :publishable_key="publishable_key" />
    {% else %}
      <c-drf-stripe.plans-unavailable />
    {% endif %}
  </c-page>
{% endblock account.content %}
```

## Before it is configured

A project that has not yet supplied `DRF_STRIPE_PRICING_TABLE_ID`, `DRF_STRIPE_PUBLISHABLE_KEY`,
or `MVP_PAYMENTS` at all, gets a page that says plans are not available — never an empty region
with nothing to explain it. `<c-drf-stripe.plans-unavailable>` renders that sentence and takes no
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

`mvp_payments/static/mvp_payments/drf_stripe/pricing_table.js` is what reveals it: after your
page's `load` event, it checks `customElements.get("stripe-pricing-table")`. Undefined means the
library never arrived, and the hidden message is shown. Load this file the way you load the
provider's own library — it emits no message of its own and fetches nothing:

```html
<script defer src="{% static 'mvp_payments/drf_stripe/pricing_table.js' %}"></script>
```

## Replacing the component or the page

Two different things can be replaced, and what each keeps differs.

### Replacing the component

Supply your own `cotton/drf_stripe/pricing_table.html`, earlier on the template search path than
this package, and every `<c-drf-stripe.pricing-table>` tag renders it instead — no view and no
query of your own is needed. The shipped page still calls the component with the same two
attributes, so this changes only what the tag itself renders; the page's URL, its
`LoginRequiredMixin`, its context and its unavailable-state branch all stay the shipped page's.

### Replacing the page

Supply your own template at `mvp_payments/drf_stripe/plans.html`, earlier on the template search
path than this package, and it is used instead — no view, no context processor and no query of
your own is needed, and `pricing_table_id` and `publishable_key` are already in the context. This
replaces everything the template decides, including whether to use the component at all; only the
view underneath it — the URL, `LoginRequiredMixin`, and the two names it puts in the context —
stays the shipped page's.

Django's app-directories template loader checks `INSTALLED_APPS` in order and uses the first
match it finds, so your own application needs to appear before `mvp_payments` in that list for its
copy to be found first — the same mechanism that requires this package itself to precede `mvp`
(see the README's Install step).
