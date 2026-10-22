# The user subscriptions page

The `stripe` namespace contributes a page showing a signed-in person every subscription they
currently hold. It arrives with the package: add `mvp_payments.stripe` to `INSTALLED_APPS`, mount
this package's URLs once, and the page is in the Account Center's navigation. There is no view to
write and no template to supply.

This page describes what that page puts in its template context, the components it is built from,
and how to replace it with one of your own.

## What counts as current

The page shows every subscription the Stripe app holds for the person that has not finished, and
does not apply a definition of its own. That is `Subscription.objects.for_user(user).current()`:
every status except `canceled` and `incomplete_expired`. So a subscription that is past due,
unpaid, incomplete or paused is shown with its status, and the way through to Stripe's portal is
there to put it right. A person with nothing current reads as having no subscription. A person who
holds several subscriptions sees every one of them.

Whether someone counts as subscribed, for deciding what they may see, is a different question,
answered by `subscribed()`. A person whose payment has failed is on this page and is not
subscribed.

That matters if you are deciding where to show something. A page that drew its own line would
disagree with the rest of your application on the day the app's line moved. See
[Asking whether a user is subscribed](stripe-app.md#asking-whether-a-user-is-subscribed).

## The context

`SubscriptionPageView` adds five names to the template context:

`subscriptions`
: A tuple of `CurrentSubscription`, newest billing period first, for the person making the
  request. Empty for someone with no customer, or nothing subscribed, which is not an error.

`billing_portal_endpoint`
: Where the Stripe app's billing-portal view is mounted, the reverse of
  `payments:stripe-billing-portal`. `None` for a person with no current subscription: there is
  nothing to manage until one exists.

`plan_switch_endpoint`
: Where the Stripe app's plan-switch view is mounted, the reverse of
  `payments:stripe-plan-switch`. `None` for a person with no current subscription. See
  [Switching plans](#switching-plans).

`plans_url`
: Where the plans page is mounted, the reverse of `payments_plans:stripe-plans`. `None` when the
  project has not included `mvp_payments.plans_urls`, in which case the page offers no way to it.
  The plans page is outside the Account Center, so this page carries the way to it, for a person
  with no subscription to choose one.

`provider_return`
: Set when the reader has just paid and nothing current shows yet: the page was reached with
  `?returned=N`, which marks the reader as just back from the provider's checkout. A dict with
  `attempt`, the `N` the page was reached with, and `poll_url`, the address the subscription region
  polls, or `None` once the polls have run out. `None` on an ordinary visit and whenever a
  subscription is showing. See [Coming back from the provider](#coming-back-from-the-provider).

Everything else on the page is reached through `subscriptions`. If you override the template you
have all of it, and you need no view, no context processor and no query of your own.

### `CurrentSubscription`

One subscription the Stripe app counts as subscribed. It carries the plan the person is paying
for, since the Stripe app records one price per subscription.

| Attribute | What it holds |
|---|---|
| `status` | The status exactly as Stripe reported it: `active` or `trialing` on the shipped page. The component renders any status it is given, as itself, since Stripe adds statuses over time. |
| `name` | The name of the product the subscription is for. |
| `amount` | A `Money` for what it costs per billing interval, or `None` for a price with no fixed amount. |
| `interval` | The unit it bills in, as Stripe reports it: `day`, `week`, `month` or `year`. |
| `interval_count` | How many intervals pass between bills. |
| `frequency_display` | The billing frequency in words, such as "every month" or "every 3 months", under the active language. An interval this table does not recognise is returned as `interval_count`'s raw form, such as `quarter_1`, rather than dropped. |
| `period_start` | When the current billing period began, or `None` where nothing is recorded. |
| `period_end` | When it ends, or `None`. |

The Stripe app records nothing about what a plan grants inside your application, so there is
nothing here about it. If you keep that record yourself, look it up from `name` in a template of your own and
place it beside the plan.

### `Money`

An amount as the provider reports it: an integer in the currency's minor unit, plus the currency
code.

| Member | What it does |
|---|---|
| `minor_units` | The integer the Stripe app recorded. Stripe's `2000` is £20.00. |
| `currency` | The three-letter code, held upper-case whatever case it arrived in. Stripe reports it lower-case and the app stores that verbatim, so the value you read here is not always the value in the database column. |
| `amount` | The same figure in the currency's own unit, as a `Decimal`. |
| `exponent` | How many decimal places this currency's minor unit sits at. |
| `str(money)` | The amount under the active locale, followed by its currency code. |

Most currencies divide into hundredths, but not all: `JPY` has no fractional unit and `BHD`
divides into thousandths, so an amount rendered on the assumption of two decimal places is wrong
by a factor of a hundred in one direction or ten in the other. `Money` knows which currencies
those are. A `Money` with no currency renders as nothing at all, because an integer with no
currency has no honest reading.

No figure here is calculated. There is no total across subscriptions, no proration and no
conversion between currencies, because the Stripe app records none of those and a number this
package worked out is a number the provider never stood behind.

## The components

Six components render the page. You can place any of them in a template of your own, and each
renders from the attributes you give it — with one exception, noted against the component it
applies to.

```html
<c-stripe.subscription :subscription="subscription" />
<c-stripe.amount :amount="subscription.amount" />
<c-stripe.plans-link :url="plans_url" :subscribed="subscriptions"
                     :switch_endpoint="plan_switch_endpoint" />
<c-stripe.portal-link :endpoint="billing_portal_endpoint" />
<c-stripe.provider-return :state="provider_return" />
<c-stripe.no-subscription />
```

`<c-stripe.subscription>`
: One subscription as a card: its status as a badge, its current billing period where there is
  one, and its plan's name, amount and billing frequency. A status the component has no colour for
  still renders, as itself, with a neutral badge.

`<c-stripe.amount>`
: A `Money`, rendered in its own currency. Given `None`, renders nothing.

`<c-stripe.plans-link>`
: The way to another plan, which depends on `subscribed`. Somebody on no plan gets "Choose a
  plan", a link to `url`, the plans page. Somebody on a plan gets "Switch plans", which posts to
  `switch_endpoint` and follows the provider's plan-change screen, the same way the portal control
  works. With no `url` for the first case, or no `switch_endpoint` for the second, it renders
  nothing at all rather than a control leading nowhere. The subscriber's control reads
  `{{ csrf_token }}` from context, as the portal control does.

`<c-stripe.portal-link>`
: Given an `endpoint`, a control that posts to it and follows the address the Stripe app answers
  with, carrying the endpoint and a CSRF token as data. Given `None`, a statement that the
  subscription is managed by the provider and the portal cannot be reached, with no control, since
  there is nowhere for it to lead. Place it only where the reader has a subscription: the shipped
  page renders the component only when there is one.

    This is the one component that needs more than its attributes. It reads `csrf_token` from the
    template context, the way every CSRF-protected form in Django does, so render it from a view
    rather than from a context you assembled yourself. Rendered without one the control looks
    right and every post it makes is rejected.

`<c-stripe.provider-return>`
: Given the page's `provider_return`, a notice that the payment is being confirmed while the page
  polls for it, or that it has not arrived yet once the polls run out. Renders nothing when given
  `None`.

`<c-stripe.no-subscription>`
: Takes no attributes. States that there is no current subscription, for someone who never had one
  and for someone whose subscription has ended alike. The shipped page renders it as the
  `{% empty %}` branch of its loop over `subscriptions`, in place of the portal control and every
  region a current subscription would have shown.

They render the daisyUI classes django-mvp already ships, so they follow your theme without any
stylesheet of their own.

## Reaching the billing portal

The Stripe app mounts a billing-portal view with the package's URLs, at `stripe/billing-portal/`
under wherever you mounted them, named `payments:stripe-billing-portal`. It answers a `POST` from
a signed-in person with `{"url": ...}`, the address of a Stripe billing-portal session for that
person's customer, and the page's script follows it. It answers 409 to a person with no customer,
302 to someone not signed in, and 502 when Stripe cannot be asked. Nothing needs configuring.

`<c-stripe.portal-link>` cannot do the posting itself — Cotton components render markup, not
JavaScript behaviour — so a small static file does it: `mvp_payments/static/mvp_payments/stripe/billing_portal.js`.
It binds every portal-link control on the page, posts, and follows the address a successful answer
carries.

It sends the CSRF token from Django's `csrftoken` cookie, not the one the component rendered.
Signing in again replaces the token, so a page left open in one tab while the person signed out and
back in in another would otherwise post a token Django refuses. The rendered token is the fallback
for a project that keeps its token in the session (`CSRF_USE_SESSIONS`).

It never sends the reader nowhere. If the post is refused, or the view redirects to the sign-in
page, the control says the page is out of date and to reload it. On any other failure it says the
portal could not be reached.

It listens for clicks on the whole document rather than binding each control when the page loads,
so a control that arrives later still works. That happens on the user subscriptions page when it polls
for a payment and swaps its own contents in.

You load that file yourself, the way you already load your project's other static assets — this
package emits no `<script>` tag of its own:

```html
<script defer src="{% static 'mvp_payments/stripe/billing_portal.js' %}"></script>
```

The demo project does this in `demo/templates/base.html`.

## Switching plans

A subscriber changes plan on the provider's own plan-change screen. That screen shows the plan they
are on, what the change costs and when it takes effect, and it changes the subscription they
already have.

The Stripe app mounts the view that opens it, at `stripe/plan-switch/`, named
`payments:stripe-plan-switch`. It works like the portal view and answers 409 to a person with
nothing subscribed. With exactly one current subscription it opens the plan-change screen for that
subscription. With several it opens the portal's home instead, since there is no one subscription
to open on, and the person picks.

Two things are set in the provider's dashboard, not here:

- **Which plans can be switched to.** The customer portal's settings list the products and prices a
  subscriber may move between. With none listed, the plan-change screen has nothing to offer.
- **Where the change reaches your records.** Stripe reports the change through the webhook (see
  [how to point Stripe at the webhook](../how-to/point-stripe-at-the-webhook.md)). Until it arrives,
  your records still show the old plan. The return view below covers the gap.

## Coming back from the provider

Stripe sends a person back to your site separately from telling the Stripe app what they bought,
so the page they land on can be reached before the app has heard. Somebody who has just paid could
be told they have no subscription.

So have the provider's checkout send them back to the user subscriptions page with `?returned=1` on the
address. Where a buyer lands after paying is the success address of the checkout, so set it to
that address.

On that visit, with nothing current showing yet, the page says the payment is being confirmed
instead of saying there is no subscription, and polls for it with htmx, which django-mvp already
loads on every page. Every three seconds it fetches the page again and swaps in only its
subscription region (`#mvp-payments-subscription`). Nothing else on the page reloads. Each poll
counts up `returned`, and the polling stops by itself as soon as a subscription appears, or after
`SubscriptionPageView.RETURN_POLL_LIMIT` polls (five). After the last one the page says the payment
has not reached the site yet and to reload later.

Once a subscription is showing, `?returned` changes nothing. Reloading the page afterwards shows
it as normal.

What makes a payment or a change arrive is Stripe's webhook reaching the Stripe app, and this only
covers the seconds in between.

The billing portal is sent back to a view of the Stripe app instead, at `stripe/return/`, named
`payments:stripe-billing-return`. It runs `Customer.sync()` for the signed-in person, so the plan
they just chose in the portal is already recorded, and redirects to this page with `?returned=1`.
When Stripe cannot be asked it redirects anyway, and the page waits for the webhook. A person with
no customer is redirected without Stripe being asked. This is what lets a development server,
which Stripe cannot reach, show a change straight away.

## Replacing the page

The shipped page is a starting point rather than a limit. Supply your own template at
`mvp_payments/stripe/subscription.html`, earlier on the template search path than this
package, and it is used instead. Everything above is already in its context — no view, no
context processor and no query of your own.

Django's app-directories template loader checks `INSTALLED_APPS` in order and uses the first
match it finds, so your own application needs to appear before `mvp_payments` in that list for
its copy to be found first. That is the same mechanism that requires this package itself to
precede `mvp` (see the README's Install step).

```html
{% extends "mvp/account/base.html" %}
{% block account.content %}
  <c-mvp.page>
    <c-mvp.page.title :title="page.title" />
    {# Polls for itself while a payment is on its way; see provider_return. #}
    <div id="mvp-payments-subscription"
         class="flex flex-col gap-6"
         {% if provider_return.poll_url %}hx-get="{{ provider_return.poll_url }}" hx-trigger="every 3s" hx-select="#mvp-payments-subscription" hx-swap="outerHTML"{% endif %}>
      <c-stripe.provider-return :state="provider_return" />
      {% for subscription in subscriptions %}
        <c-stripe.subscription :subscription="subscription" />
      {% empty %}
        {% if not provider_return %}
          <c-stripe.no-subscription />
        {% endif %}
      {% endfor %}
      <div class="flex flex-wrap items-start gap-3"
           data-mvp-payments-subscription-actions>
        <c-stripe.plans-link :url="plans_url"
                           :subscribed="subscriptions"
                           :switch_endpoint="plan_switch_endpoint" />
        {% if subscriptions %}
          <c-stripe.portal-link :endpoint="billing_portal_endpoint" />
        {% endif %}
      </div>
    </div>
  </c-mvp.page>
{% endblock account.content %}
```

That is the shipped template in full. Change the wording, change the arrangement, drop the
components and write your own markup against `subscriptions` directly, or keep the components and
put something of yours beside them.

## Under the page

Two classes do the work, and you only need them if you are building something beyond a template.

`SubscriptionReader`
: `SubscriptionReader.for_user(user)` returns the tuple of `CurrentSubscription` described above.
  It reaches the Stripe app's `Subscription` model through Django's application registry and
  imports nothing from it.

`SubscriptionPageView`
: The page's view, built on `PaymentPageView`. It requires a signed-in person and makes no finer
  decision than that, because this package holds no entitlement information. Who among your
  signed-in people may see this page is yours to enforce.
