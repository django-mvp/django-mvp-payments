# The subscription page

The `drf-stripe` namespace contributes a page showing a signed-in person what they are currently
subscribed to. It arrives with the package: install this alongside
[drf-stripe-subscription](https://github.com/oscarychen/drf-stripe-subscription), mount this
package's URLs once, and the page is in the Account Center's navigation. There is no view to
write and no template to supply.

This page describes what that page puts in its template context, the components it is built from,
and how to replace it with one of your own.

## What counts as current

The page shows the subscriptions the backend itself treats as current, and does not apply a
definition of its own. The backend grants access on a fixed set of statuses and answers every
other question about a person from that same set, so a subscription that has been cancelled, has
ended or has gone unpaid does not appear here, and a person with none of them reads as having no
current subscription.

That matters if you are deciding where to show something. A page that drew its own line would
disagree with the rest of your application on the day the backend's line moved.

## The context

`SubscriptionPageView` adds five names to the template context:

`subscriptions`
: A tuple of `CurrentSubscription`, newest first, for the person making the request. Empty for
  someone the backend holds no customer record for, which is not an error.

`billing_portal_endpoint`
: Where the backend's own billing-portal endpoint is mounted, read from
  `MVP_PAYMENTS["DRF_STRIPE_BILLING_PORTAL"]` in your settings. `None` when that setting is
  absent, and `None` for a person with no current subscription even when it is set — the backend's
  endpoint creates a customer at the provider for whoever posts to it, so it is never offered to
  someone with nothing to manage.

`plan_switch_endpoint`
: Where your project mounted an endpoint that opens the provider's plan-change screen for this
  person's subscription, read from `MVP_PAYMENTS["DRF_STRIPE_PLAN_SWITCH"]`. `None` when that
  setting is absent, and `None` for a person with no current subscription. See
  [Switching plans](#switching-plans).

`plans_url`
: Where the plans page is mounted. The plans page is not in the Account Center's navigation, so
  this page carries the way to it, for a person with no subscription to choose one.

`provider_return`
: Set when the reader has just paid and nothing current shows yet: the page was reached with
  `?returned=N`, which marks the reader as just back from the provider's checkout. A dict with
  `attempt`, the `N` the page was reached with, and `poll_url`, the address the subscription region
  polls, or `None` once the polls have run out. `None` on an ordinary visit and whenever a
  subscription is showing. See [Coming back from the provider](#coming-back-from-the-provider).

Everything else on the page is reached through `subscriptions`. If you override the template you
have all of it, and you need no view, no context processor and no query of your own.

### `CurrentSubscription`

One subscription the backend currently grants access for.

| Attribute | What it holds |
|---|---|
| `status` | The status exactly as the backend recorded it, such as `active`, `trialing` or `past_due`. Providers add statuses over time, so treat this as an open set rather than a fixed one. |
| `period_start` | When the current billing period began, or `None` where the backend recorded nothing. |
| `period_end` | When it ends, or `None`. |
| `plans` | A tuple of `Plan`, one per priced item the subscription covers. |

### `Plan`

One priced item on a subscription. A subscription can cover several.

| Attribute | What it holds |
|---|---|
| `name` | The price's nickname where the project set one, and the product's name otherwise. |
| `amount` | A `Money`. |
| `frequency` | The backend's own encoding of the billing frequency, such as `month_1`. |
| `frequency_display` | The same in words, such as "every month" or "every 3 months", under the active language. An encoding this table does not recognise is returned unchanged rather than dropped. |
| `quantity` | How many of this item the subscription covers. |
| `features` | A tuple of `PlanFeature` recorded against this plan's product, empty where the project recorded none. |

### `PlanFeature`

Something a plan grants inside your application, recorded by you against the product in the
provider's dashboard rather than held here.

| Attribute | What it holds |
|---|---|
| `identifier` | The feature id you set on the product. |
| `description` | Your description of it, falling back to the identifier where you gave none. |

drf-stripe-subscription reads a product's features from a space-delimited `features` key in that
product's Stripe metadata, and syncs each id into its own record, with a description you set
separately. A product you have set none on is normal, and its plan's `features` is simply empty.

### `Money`

An amount as the provider reports it: an integer in the currency's minor unit, plus the currency
code.

| Member | What it does |
|---|---|
| `minor_units` | The integer the backend recorded. Stripe's `2000` is £20.00. |
| `currency` | The three-letter code, held upper-case whatever case it arrived in. The provider reports it lower-case and the backend stores that verbatim, so the value you read here is not always the value in the database column. |
| `amount` | The same figure in the currency's own unit, as a `Decimal`. |
| `exponent` | How many decimal places this currency's minor unit sits at. |
| `str(money)` | The amount under the active locale, followed by its currency code. |

Most currencies divide into hundredths, but not all: `JPY` has no fractional unit and `BHD`
divides into thousandths, so an amount rendered on the assumption of two decimal places is wrong
by a factor of a hundred in one direction or ten in the other. `Money` knows which currencies
those are. A `Money` with no currency renders as nothing at all, because an integer with no
currency has no honest reading.

No figure here is calculated. There is no total across a subscription's items, no proration and
no conversion between currencies, because the backend records none of those and a number this
package worked out is a number the provider never stood behind.

## The components

Eight components render the page. You can place any of them in a template of your own, and each
renders from the attributes you give it — with one exception, noted against the component it
applies to.

```html
<c-drf-stripe.subscription :subscription="subscription" />
<c-drf-stripe.plan :plan="plan" />
<c-drf-stripe.amount :amount="plan.amount" />
<c-drf-stripe.features :features="plan.features" />
<c-drf-stripe.plans-link :url="plans_url" :subscribed="subscriptions"
                         :switch_endpoint="plan_switch_endpoint" />
<c-drf-stripe.portal-link :endpoint="billing_portal_endpoint" />
<c-drf-stripe.provider-return :state="provider_return" />
<c-drf-stripe.no-subscription />
```

`<c-drf-stripe.subscription>`
: One subscription as a card: its status as a badge, its current billing period where there is
  one, and each of its plans. A status the component has no colour for still renders, as itself,
  with a neutral badge.

`<c-drf-stripe.plan>`
: One priced item: its name, its quantity where more than one, its amount, its billing frequency,
  and its features beneath it.

`<c-drf-stripe.amount>`
: A `Money`, rendered in its own currency.

`<c-drf-stripe.features>`
: A plan's `features`, one line each, its description where the project gave one and its
  identifier otherwise. Given none, renders nothing at all — no heading and no empty list.

`<c-drf-stripe.plans-link>`
: The way to another plan, which depends on `subscribed`. Somebody on no plan gets "Choose a
  plan", a link to `url`, the plans page. Somebody on a plan gets "Switch plans", which posts to
  `switch_endpoint` and follows the provider's plan-change screen, the same way the portal control
  works. A subscriber is never sent to the plans page, because the pricing table there cannot show
  which plan they are on, and buying from it starts a second subscription beside the first. With no
  `url` for the first case, or no `switch_endpoint` for the second, it renders nothing at all
  rather than a control leading nowhere. The subscriber's control reads `{{ csrf_token }}` from
  context, as the portal control does.

`<c-drf-stripe.portal-link>`
: Given an `endpoint`, a control that posts to it and follows the address the backend answers
  with, carrying the endpoint and a CSRF token as data. Given `None`, a statement that the
  subscription is managed by the provider and the portal cannot be reached, with no control, since
  there is nowhere for it to lead. Place it only where the reader has a subscription: that second
  wording addresses somebody who has one and whose project has not set the endpoint, and the
  shipped page renders the component only when there is a subscription for exactly that reason.

    This is the one component that needs more than its attributes. It reads `csrf_token` from the
    template context, the way every CSRF-protected form in Django does, so render it from a view
    rather than from a context you assembled yourself. Rendered without one the control looks
    right and every post it makes is rejected.

`<c-drf-stripe.provider-return>`
: Given the page's `provider_return`, a notice that the payment is being confirmed while the page
  polls for it, or that it has not arrived yet once the polls run out. Renders nothing when given
  `None`.

`<c-drf-stripe.no-subscription>`
: Takes no attributes. States that there is no current subscription, for someone who never had one
  and for someone whose subscription has ended alike — the backend reports both the same way, and
  this package has no information that would let it say more. The shipped page renders it as the
  `{% empty %}` branch of its loop over `subscriptions`, in place of the portal control and every
  region a current subscription would have shown.

They render the daisyUI classes django-mvp already ships, so they follow your theme without any
stylesheet of their own.

## Reaching the billing portal

The page hands a reader to an endpoint that answers a `POST` with `{"url": ...}`. It carries no
route name of its own, so it cannot be linked to directly or reversed — you tell the page where
you mounted it:

```python
MVP_PAYMENTS = {
    "DRF_STRIPE_BILLING_PORTAL": "/api/stripe/customer-portal/",
}
```

### The backend's own endpoint raises after its first use

`drf-stripe-subscription` ships that endpoint at `customer-portal/`, and today it succeeds exactly
once per person. `get_or_create_stripe_user(user_id=...)` looks a customer record up by
`(user_id, customer_id=None)`. The first call creates that record and then fills the second field
in, so every call after it matches nothing, tries to insert a second record for a person who
already has one, and the database refuses with a unique-constraint error. It is open on the
backend's own tracker.

Until that is fixed, point this setting at an endpoint of your own that does the same two things
either side of the broken lookup — read the customer identifier the backend already keeps, and ask
the provider for a session. `demo/views.py` has a working one, at about twenty lines.

This package cannot ship that endpoint for you. It reaches a provider only through a backend's
HTTP endpoints and imports no provider SDK at all, which Article XII of the constitution makes
absolute and `tests/test_app.py` enforces. A project of your own is bound by neither.

`<c-drf-stripe.portal-link>` cannot do the posting itself — Cotton components render markup, not
JavaScript behaviour — so a small static file does it: `mvp_payments/static/mvp_payments/drf_stripe/billing_portal.js`.
It binds every portal-link control on the page, posts, and follows the address a successful answer
carries.

It sends the CSRF token from Django's `csrftoken` cookie, not the one the component rendered.
Signing in again replaces the token, so a page left open in one tab while the person signed out and
back in in another would otherwise post a token Django refuses. The rendered token is the fallback
for a project that keeps its token in the session (`CSRF_USE_SESSIONS`).

It never sends the reader nowhere. If the post is refused, or the endpoint redirects to the sign-in
page, the control says the page is out of date and to reload it. On any other failure it says the
portal could not be reached.

It listens for clicks on the whole document rather than binding each control when the page loads,
so a control that arrives later still works. That happens on the subscription page when it polls
for a payment and swaps its own contents in.

You load that file yourself, the way you already load your project's other static assets — this
package emits no `<script>` tag of its own:

```html
<script defer src="{% static 'mvp_payments/drf_stripe/billing_portal.js' %}"></script>
```

The demo project does both of these in `demo/settings.py` and `demo/templates/base.html`, and
points the setting at its own endpoint rather than the backend's for the reason above.

## Switching plans

A subscriber changes plan on the provider's own plan-change screen, not on the plans page. That
screen shows the plan they are on, what the change costs and when it takes effect, and it changes
the subscription they already have. The provider's pricing table knows none of that, and a
purchase through it starts a second subscription.

Neither the backend nor this package ships an endpoint that opens that screen. The backend has
none, and this package may not call a provider. So, as with the portal, your project mounts one and
tells the page where it is:

```python
MVP_PAYMENTS = {
    "DRF_STRIPE_PLAN_SWITCH": "/api/plan-switch/",
}
```

It answers a `POST` with `{"url": ...}`, like the portal endpoint, and `billing_portal.js` binds
the control the same way. The endpoint creates a billing portal session for the person's customer
record with `flow_data` of type `subscription_update`, naming their current subscription.
`PlanSwitchView` in `demo/views.py` is a working one.

Two things are set in the provider's dashboard, not here:

- **Which plans can be switched to.** The customer portal's settings list the products and prices a
  subscriber may move between. With none listed, the plan-change screen has nothing to offer.
- **Where the change reaches your records.** The provider reports the change through webhooks,
  which the backend handles. Until they arrive, your records still show the old plan. The demo has
  no webhooks, so it sends the reader back through a view that asks the provider for the current
  state first.

Without the setting, a subscriber is offered no "Switch plans" control. The portal control still
reaches the portal, which offers the same change if the portal's settings allow it.

## Coming back from the provider

The provider sends a person back to your site separately from telling the backend what they
bought, so the page they land on can be reached before the backend has heard. Somebody who has
just paid could be told they have no subscription.

So have the provider's checkout send them back to the subscription page with `?returned=1` on the
address. In the provider's dashboard, set the pricing table to redirect to your website after
payment, at that address.

On that visit, with nothing current showing yet, the page says the payment is being confirmed
instead of saying there is no subscription, and polls for it with htmx, which django-mvp already
loads on every page. Every three seconds it fetches the page again and swaps in only its
subscription region (`#mvp-payments-subscription`). Nothing else on the page reloads. Each poll
counts up `returned`, and the polling stops by itself as soon as a subscription appears, or after
`SubscriptionPageView.RETURN_POLL_LIMIT` polls (five). After the last one the page says the payment
has not reached the site yet and to reload later.

Once a subscription is showing, `?returned` changes nothing. Reloading the page afterwards shows
it as normal, and so does coming back from the portal. The page cannot tell whether a change made
in the portal has landed yet, so it shows the subscription as the backend currently has it.

What makes a payment or a change arrive is the provider's webhooks reaching the backend, and this
only covers the seconds in between. The demo has no webhooks, so its return address is a view that
asks the provider for the current state first and then redirects here with `?returned=1`.

## Replacing the page

The shipped page is a starting point rather than a limit. Supply your own template at
`mvp_payments/drf_stripe/subscription.html`, earlier on the template search path than this
package, and it is used instead. Everything above is already in its context — no view, no
context processor and no query of your own.

Django's app-directories template loader checks `INSTALLED_APPS` in order and uses the first
match it finds, so your own application needs to appear before `mvp_payments` in that list for
its copy to be found first. That is the same mechanism that requires this package itself to
precede `mvp` (see the README's Install step).

```html
{% extends "mvp/account/base.html" %}
{% block account.content %}
  <c-page>
    <c-page.title :title="page.title" />
    {# Polls for itself while a payment is on its way; see provider_return. #}
    <div id="mvp-payments-subscription"
         class="flex flex-col gap-6"
         {% if provider_return.poll_url %}hx-get="{{ provider_return.poll_url }}" hx-trigger="every 3s" hx-select="#mvp-payments-subscription" hx-swap="outerHTML"{% endif %}>
      <c-drf-stripe.provider-return :state="provider_return" />
      {% for subscription in subscriptions %}
        <c-drf-stripe.subscription :subscription="subscription" />
      {% empty %}
        {% if not provider_return %}
          <c-drf-stripe.no-subscription />
        {% endif %}
      {% endfor %}
      {# Both ways onward on one line, wrapping on a narrow screen. #}
      <div class="flex flex-wrap items-start gap-3"
           data-mvp-payments-subscription-actions>
        <c-drf-stripe.plans-link :url="plans_url"
                                 :subscribed="subscriptions"
                                 :switch_endpoint="plan_switch_endpoint" />
        {% if subscriptions %}
          <c-drf-stripe.portal-link :endpoint="billing_portal_endpoint" />
        {% endif %}
      </div>
    </div>
  </c-page>
{% endblock account.content %}
```

That is the shipped template in full. Change the wording, change the arrangement, drop the
components and write your own markup against `subscriptions` directly, or keep the components and
put something of yours beside them.

## Under the page

Two classes do the work, and you only need them if you are building something beyond a template.

`SubscriptionReader`
: `SubscriptionReader.for_user(user)` returns the tuple of `CurrentSubscription` described above.
  It reaches the backend through Django's application registry and imports nothing from it, so
  this package carries no dependency on the backend and never has to be replaced alongside it.

`SubscriptionPageView`
: The page's view, built on `PaymentPageView`. It requires a signed-in person and makes no finer
  decision than that, because this package holds no entitlement information. Who among your
  signed-in people may see this page is yours to enforce.
