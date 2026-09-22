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
| `customer_email` | Declared on the component. Not yet read — a later story wires it to the signed-in person's address. |

The component reads no settings and imposes no sign-in requirement, so it can be placed on any
page of your own project, whether or not this package's Account Center pages are in use.

## The page

`PlansPageView` adds two names to the template context, read from your settings at render time:

`pricing_table_id`
: `MVP_PAYMENTS["DRF_STRIPE_PRICING_TABLE_ID"]` — the pricing table's id, from the provider's
  dashboard. `None` when the setting is absent.

`publishable_key`
: `MVP_PAYMENTS["DRF_STRIPE_PUBLISHABLE_KEY"]` — the account's publishable key. `None` when the
  setting is absent.

```python
MVP_PAYMENTS = {
    "DRF_STRIPE_PRICING_TABLE_ID": "prctbl_...",
    "DRF_STRIPE_PUBLISHABLE_KEY": "pk_...",
}
```

The shipped page renders the component with both values unconditionally. It keeps
`LoginRequiredMixin`, so an anonymous visitor is sent to sign in rather than shown the page.

```html
{% extends "mvp/account/base.html" %}
{% block account.content %}
  <c-page>
    <c-page.title :title="page.title" />
    <c-drf-stripe.pricing-table :table_id="pricing_table_id"
                                 :publishable_key="publishable_key" />
  </c-page>
{% endblock account.content %}
```

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

## Replacing the page

Supply your own template at `mvp_payments/drf_stripe/plans.html`, earlier on the template search
path than this package, and it is used instead — no view, no context processor and no query of
your own is needed, and `pricing_table_id` and `publishable_key` are already in the context.
