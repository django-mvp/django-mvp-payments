# The plans page

The plans page shows every visitor the plans they can choose from. It draws them itself from the
prices in your Stripe account, so a price you add in Stripe's dashboard appears on the page
without a change to your project.

It is a page of its own, outside the Account Center, and it is open to everyone. A project mounts
it with a second include, beside the single include of `mvp_payments.urls`, at the address it
chooses. Nothing is routed until the project includes it, and nothing is routed at all unless
`mvp_payments.stripe` is in `INSTALLED_APPS`.

## Mounting

```python
urlpatterns = [
    path("account/billing/", include("mvp_payments.urls")),
    path("plans/", include("mvp_payments.plans_urls")),
]
```

The page is then reached as `payments_plans:stripe-plans`, here at `/plans/`. The user
subscriptions page links to it through its `plans_url` name, which is `None` while the project has
not included `mvp_payments.plans_urls`. The page has no entry in the Account Center's navigation.
To put it in your own navigation, name `payments_plans:stripe-plans` as the view of a menu item.

## What the page shows

A plan is a Stripe price, shown under its product. A product with a monthly and a yearly price
gives two plans, and the page offers both.

A price is on offer when it is active, recurring, billed per unit with a fixed amount, and
licensed rather than metered, and its product is active. A tiered or metered price has no single amount to show, so it is left out. Products come cheapest first,
and a product's prices come shortest billing period first.

Each card shows the product's name, the price's amount in its own currency, how often it bills,
the product's description and its marketing features. A product with no description or no
features shows neither, and nothing stands in their place. Text that comes from Stripe is
escaped. When the prices have more than one billing frequency, a switch above the cards chooses
which frequency is shown, and without JavaScript every frequency is shown, each under its own
heading.

Two states stand in for the cards:

- When Stripe could not be read (no secret key is set, or Stripe failed), the page says the plans
  cannot be shown. The failure is remembered for 60 seconds, so an outage does not slow every
  visit.
- When Stripe holds no price on offer, the page says there are no plans to choose from.

Amounts go through `mvp_payments.money.Money`, so a zero-decimal currency such as the yen shows
`500,000 JPY` and a three-decimal one such as the Kuwaiti dinar shows `12.500 KWD`.

## Buying a plan

Each card ends in one control, which depends on who is looking:

| Reader | Control |
|---|---|
| Not signed in | A link to `login_url` with `next` set to this page, `?plan=<price id>` and the card's anchor, so signing in lands on the plan they picked |
| Signed in | A form that posts `price` and `return_to` to [`CheckoutView`](stripe-app.md), which sends them to Stripe's checkout page |
| Holds the plan | A link to the user subscriptions page. A plan whose subscription has ended is offered again |

The picked plan's billing frequency is selected when the page opens and its card is the target of
the anchor. Every control is named for its plan, by text only a screen reader hears, and is
described by the note under the cards that payment is taken on Stripe's checkout page. A checkout
that cannot start returns the reader to this page with a message above it.

## Where the prices come from

The Stripe app reads the prices from Stripe and keeps them in your project's default cache for
`MVP_PAYMENTS["STRIPE_CATALOGUE_TIMEOUT"]` seconds, an hour when it is not set. A visit while
they are cached makes no request to Stripe. A price changed in Stripe's dashboard shows on the
page when the cached list expires, or sooner when a product or price webhook arrives or
`stripe_sync` runs. Those two clear the list from other processes, so they reach the page only
when your default cache is shared across processes, not a local-memory or dummy one. The catalogue, the cache key and the failure handling
are described in [the Stripe app reference](stripe-app.md#the-catalogue).

## The parts

The page is built from parts that each work on their own, so a project can draw the plans on a page
of its own, with the same parts or with its own markup for some of them.

`<c-stripe.plans :plans="plans" />`
: Every plan on offer, one card per price, behind the frequency switch.

`<c-stripe.plan-card :price="price" :plans="plans" />`
: One plan: the product's name, the price, the description, the features and the way to buy it.
  A plan the signed-in person already holds carries a badge, and a plan they picked before signing
  in stands out.

`<c-stripe.plan-price :price="price" />`
: A price's amount and how often it bills.

`<c-stripe.plan-features :product="product" />`
: A product's marketing features as a list, or nothing when it has none.

`<c-stripe.plan-choose :price="price" :plans="plans" />`
: The way to buy one plan. A signed-in person gets a button that submits the price to the checkout
  address. A visitor who is not signed in gets a link to sign in that brings them back to the page
  with the plan they picked marked. A person who holds the plan gets a link to their user
  subscriptions page.

`<c-stripe.no-plans />` and `<c-stripe.plans-unavailable />`
: The two states above. Neither takes anything.

## The data the parts read

`plans` is a dictionary. The page puts it in its template context under that name, and the tag
below returns the same dictionary for any template.

`prices`
: The plans on offer, as the catalogue returns them: Stripe prices with `id`, `unit_amount`,
  `currency`, `recurring` (`interval`, `interval_count`) and the product expanded under
  `product` (`id`, `name`, `description`, `marketing_features`). An empty list when nothing is on
  offer, and `None` when Stripe could not be read.

`intervals`
: The distinct billing frequencies among the prices, shortest first, each a dictionary with a
  `key` such as `month_1` and a `label` for the switch.

`first_interval`
: The key of the frequency the switch starts on: that of the plan picked before signing in,
  otherwise the shortest.

`held`
: The price ids the signed-in person currently subscribes to. Empty for a visitor.

`ready`
: The price id the visitor picked before signing in, read from `?plan=` on the address.

`signed_in`
: Whether the reader is signed in.

`login_url`, `checkout_url`, `subscriptions_url`
: The project's sign-in address, the checkout address and the user subscriptions page.

`return_to`
: The path of the page the plans are on, so signing in and a cancelled checkout come back to it.

`PlanChoices.for_request(request)`, in `mvp_payments.namespaces.stripe_plans`, builds that
dictionary. The page and the tag both call it, and a view of your own can too.

## The tag and the filters

Load `mvp_payments` to use them.

`{% stripe_plans as plans %}`
: Puts the same dictionary in any template whose context carries `request`, with no view of your
  own.

`price|price_money`
: A price's amount as a `Money` in its own currency, or `None` when it has no amount.

`price|price_frequency`
: How often a price bills in words, such as "every month" or "every 3 months". An interval this
  package does not recognise is shown as itself, such as `quarter_1`, never dropped.

`price|price_interval`
: A price's frequency key, such as `month_1`, the value the switch selects.

```html
{% load mvp_payments %}
{% stripe_plans as plans %}
{% if plans.prices %}<c-stripe.plans :plans="plans" />{% endif %}
```

## Placing and replacing

### Placing the plans on a page of your own

Use the tag and the `<c-stripe.plans>` component in any template whose context carries `request`.
No view of your own is needed, and nothing calls Stripe from your project:

```html
{% load mvp_payments %}
{% stripe_plans as plans %}
{% if plans.prices %}
  <section id="pricing">
    <c-stripe.plans :plans="plans" />
  </section>
{% endif %}
```

It shows the same plans as the plans page, with the same ways to buy. A visitor who is not signed
in goes through sign-in and comes back to the page the plans are on, with the plan they picked
ready. A signed-in person starts checkout exactly as they do from the plans page, and a cancelled
or failed checkout returns them to the page they started from.

Without `mvp_payments.stripe` in `INSTALLED_APPS`, `plans.prices` is `None` and
`<c-stripe.plans>` renders nothing, so the guard above is all a page needs to work in a project
that has not installed the Stripe app.

### Replacing a part everywhere

Supply your own copy of the part's template at `cotton/stripe/<part>.html`, earlier on the
template search path than this package. Every card then uses it. For example, to show a product's
features your own way, add `cotton/stripe/plan_features.html` to your application:

```html
<c-vars product />
<p>{{ product.name }} includes {{ product.marketing_features|length }} features.</p>
```

The part receives what the package's own version receives, under the same names. For
`plan_features` that is `product`, the Stripe product with its fields as Stripe names them. The
parts and what each receives are listed under [The parts](#the-parts). Your own application has to
appear before `mvp_payments` in `INSTALLED_APPS`, because Django's app-directories loader uses the
first match it finds.

### Replacing a part on one page

Loop over `plans.prices` yourself and compose the parts you keep, writing your own markup for the
one you replace. Every other placement is unaffected:

```html
{% for price in plans.prices %}
  <article>
    <h3>{{ price.product.name }}</h3>
    <c-stripe.plan-price :price="price" />
    <p>{{ price.product.description }}</p>
    <c-stripe.plan-choose :price="price" :plans="plans" />
  </article>
{% endfor %}
```

To replace the whole page, supply your own template at `mvp_payments/stripe/plans.html`. It
receives `plans` in its context and replaces everything the template decides. The view underneath
it, the address and the page being open to everyone, stay the shipped page's.

Your own application has to appear before `mvp_payments` in `INSTALLED_APPS` here too.
