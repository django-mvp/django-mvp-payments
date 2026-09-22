# Research — 003 Offer plans through the provider's own pricing table

What was read before planning, and what each reading settled. Everything here is a fact about a
dependency or a provider, not a choice; the choices are in `plan.md` and `decisions.md`.

## The provider's embed: what the element takes

Read: the provider's own published guide to the embeddable pricing table, 2026-09-22.

The dashboard issues two things together — a `<script>` tag pointing at
`https://js.stripe.com/v3/pricing-table.js`, and a `<stripe-pricing-table>` custom element. The
element carries its configuration entirely in attributes:

| Attribute | What it is | Used here |
|---|---|---|
| `pricing-table-id` | identifies the table built in the dashboard | yes, required (FR-001) |
| `publishable-key` | identifies the account; the provider prints it in its own copy-paste examples | yes, required (FR-001) |
| `customer-email` | prefills the checkout session's email address | yes, when known (FR-005) |
| `client-reference-id` | an opaque value echoed back on the completed checkout | no — see below |
| `customer-session-client-secret` | passes an existing customer | no; needs a server-side call the package may not make |

`client-reference-id` is the attribute built for exactly the reconciliation problem FR-005 solves,
and it is not used, because the installed backend reads it nowhere (see below). Passing a value
nothing consumes would look like a guarantee and provide none.

The element renders nothing at all when its script has not loaded. There is no event, no error and
no fallback content — the custom element is simply undefined, and an undefined custom element is
an empty inline box. This is the whole reason FR-010 exists, and it also fixes how FR-010 is
detected: `customElements.get("stripe-pricing-table")` is undefined exactly when the project did
not load the library, or when the provider's origin is blocked for that reader. Those are the two
conditions US-4's third scenario and the specification's last edge case name, and one check covers
both.

Self-hosting the library is forbidden by the provider's own terms, so it must come from their
network. That is the provider's constraint and the reason Article XIII's split exists rather than
a recommendation this package could make differently.

## The backend: how a purchase finds its person

Read: `drf_stripe/stripe_api/customers.py` in drf-stripe-subscription 1.2.2, the version the demo
and the test settings install.

`_get_or_create_stripe_user_from_customer_id` retrieves the customer from the provider, then looks
for a Django user with:

```python
django_user_query_filters = {drf_stripe_settings.DJANGO_USER_EMAIL_FIELD: customer.email}
```

The email address is the entire lookup. No other identifier is read anywhere on that path, and in
particular `client_reference_id` is never consulted. Where no user holds the address, the backend
either creates one from `USER_CREATE_DEFAULTS_ATTRIBUTE_MAP` or raises
`CreatingNewUsersDisabledError` — so an address the person typed themselves produces either a
second account or a purchase attached to nobody.

This confirms the assumption the specification rests FR-005 on, and it is why the address is
passed as an attribute rather than left to the person at checkout.

## What is already here to build on

- `PaymentPageView` and `SubscriptionPageView` in `mvp_payments/views.py`. The second is the
  precedent for a page that reads its configuration from `settings.MVP_PAYMENTS` and hands it to
  the template — it already does exactly that for the backend's portal endpoint.
- `Page.view`, added by the previous feature, is how a contribution names the view for one of its
  pages. The plans page currently names none and gets the generic one.
- `cotton/drf_stripe/portal_link.html` and `static/mvp_payments/drf_stripe/billing_portal.js` are
  the shape this feature's failure message follows: a `hidden` element in the component's own
  markup, revealed by a small static file with no build step.
- `tests/markup.py` narrows an assertion to one region of a rendered Account Center, which the
  page tests need because the word "Plans" is in the navigation as well as on the page.

## Rejected without further reading

- **Reading the provider's catalogue to render our own plan grid.** Settled at the spec gate and
  recorded in `decisions.md`; not reopened here.
- **A build step or bundler for the failure check.** Article XIII forbids it and the check is four
  lines.
- **Feature-detecting the element by waiting for it to paint.** Timing-based, flaky, and it would
  claim to detect states — an archived table, a mismatched key pair — that the specification
  explicitly leaves to the provider to render.
