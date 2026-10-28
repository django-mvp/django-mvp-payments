# Stripe app reference

`mvp_payments.stripe` keeps a small copy of each user's Stripe subscription in your project's
database. Stripe stays the source of truth: the app records who each user's Stripe customer is
and that customer's subscriptions, with their status, price and period, and refreshes the copy
from Stripe whenever Stripe reports a change. It adds no payment logic. A plan is chosen on
the plans page; paying for it, switching, cancelling and updating a card all happen on Stripe's
own hosted pages.

To set it up, see [how to install the Stripe app](../how-to/install-the-stripe-app.md) and
[how to point Stripe at the webhook](../how-to/point-stripe-at-the-webhook.md).

## Settings

Every setting lives in the `MVP_PAYMENTS` dictionary and is read only from there.

`STRIPE_SECRET_KEY`
: Your Stripe secret key, `sk_...` or `rk_...`. Required. Every call the app makes to Stripe is
  authorised with it.

`STRIPE_WEBHOOK_SECRET`
: The signing secret of the webhook endpoint Stripe sends events to, `whsec_...`. Required. Every
  webhook is verified against it.

`STRIPE_CATALOGUE_TIMEOUT`
: How many seconds the list of plans read from Stripe is kept in your project's cache. Optional,
  `3600` (an hour) when not set. See [The catalogue](#the-catalogue).

`STRIPE_TIMEOUT`
: How many seconds one request to Stripe may take before the app gives up on it. Optional, `10`
  when not set. A request that times out, cannot connect or meets an error on Stripe's side is
  tried twice more before the app reports it as a failure. Stripe answers every call the app makes
  in well under a second, and a worker left waiting is one a page cannot use.

Neither secret value appears in a template, a log message or an error page. The webhook marks the
signing secret as sensitive, so an error report Django builds with `DEBUG` off, such as the one
`AdminEmailHandler` mails, shows it as stars. The app also never reads or
writes the Stripe SDK's own module-level configuration, so another integration in the same
process cannot change the key or the API version the app uses.

When Stripe refuses a call, the app logs the kind of error and never Stripe's message, which can
repeat part of a key. Stripe's own SDK writes its requests and responses to the `stripe` logger,
at info and debug level, so leave that logger above those levels in production.

## System checks

| Check | Raised when |
|---|---|
| `mvp_payments_stripe.E001` | `MVP_PAYMENTS["STRIPE_SECRET_KEY"]` is missing or empty |
| `mvp_payments_stripe.E002` | `MVP_PAYMENTS["STRIPE_WEBHOOK_SECRET"]` is missing or empty |
| `mvp_payments_stripe.W001` | `CACHES["default"]` is Django's dummy cache, so the catalogue is never kept and every view of the plans page asks Stripe |

A message names the setting. It never prints a value.

## The Stripe API version

Every call carries the API version the app is written against, `mvp_payments.stripe.client.API_VERSION`,
rather than your account's default. Changing your account's default version does not change what
the app receives.

## Records

Both tables carry the `mvp_payments_stripe` label.

### `Customer`

One row per user who has a Stripe customer, tied to the user by `user` (reverse name
`stripe_customer`). The customer is made when the user first starts a checkout, so a row says
nothing about whether they ever paid. Deleting the user deletes the customer and its subscriptions here. Nothing is
changed on Stripe, unless the account is deleted through django-mvp-compliance with the app's
kinds declared ([Personal data](#personal-data)).

| Field | Holds |
|---|---|
| `user` | The user the customer belongs to. One customer per user |
| `stripe_id` | Stripe's customer identifier. Unique |
| `created` | When the customer was first recorded here |

### `Subscription`

`Subscription.objects` is a `SubscriptionQuerySet`, described under
[Asking whether a user is subscribed](#asking-whether-a-user-is-subscribed).

One row per Stripe subscription, reached from a customer as `customer.subscriptions`. A user who
subscribes twice has two rows. Newest billing period first is the default order.

| Field | Holds |
|---|---|
| `customer` | The customer the subscription belongs to |
| `stripe_id` | Stripe's subscription identifier. Unique |
| `status` | The status exactly as Stripe reported it, including a status this version does not know |
| `price_id` | Stripe's price identifier |
| `product_name` | The name of the price's product |
| `amount` | The price in the currency's minor unit, as Stripe reports it. `2000` in `usd` is $20.00, and `1500` in `jpy` is ¥1,500. Empty for a price with no fixed amount |
| `currency` | The lower-case ISO currency code |
| `interval`, `interval_count` | How often it bills: `month` and `1` is monthly, `month` and `3` is quarterly |
| `current_period_start`, `current_period_end` | The billing period Stripe reported |
| `cancel_at_period_end` | Whether it ends when the period does |
| `ended_at` | When it ended, if it has |
| `updated` | When the row was last written from Stripe |

Records change only from what Stripe reports. Nothing here is edited by hand.

## The catalogue

`mvp_payments.stripe.catalogue.Catalogue` reads the plans a project offers from Stripe and keeps
them in Django's default cache, under the key `mvp_payments_stripe:catalogue`. Nothing is stored in
the database. Your project's default cache decides how widely the list is shared: a local-memory
cache keeps one copy per process, and a shared cache (Redis, Memcached, a database or file cache)
keeps one copy for all of them.

The list is forgotten when `STRIPE_CATALOGUE_TIMEOUT` seconds have passed, when a verified
`product.*` or `price.*` webhook arrives, and when `stripe_sync` runs. The webhook and the command
run in their own processes, so they reach the page only through a cache the processes share. With a
local-memory or dummy cache, a change in Stripe's dashboard shows when each process's copy expires.
A dummy cache keeps nothing at all, so every view of the plans page asks Stripe, and the
`mvp_payments_stripe.W001` check warns about it.

A price is on offer when it is active, recurring, billed per unit with a fixed amount, licensed
(not metered), and its product is active. Tiered, metered, one-off and no-amount prices are left
out, because a page cannot show one honest amount for them.

`Catalogue.prices()`
: Every price on offer, as plain dictionaries with the product expanded. Products come cheapest
  first within a currency (amounts are compared as they stand, with no conversion), with each product's prices together and the shortest billing period first. Reads every
  page from Stripe on a cache miss. Returns `None`, and caches nothing, when
  `STRIPE_SECRET_KEY` is not set. Returns `None` when Stripe cannot be asked, and remembers that
  for 60 seconds under the same key, so an outage does not hold a worker on every request. The
  log names the kind of error and never Stripe's message.

`Catalogue.price(price_id)`
: The price on offer with that id, or `None`.

`Catalogue.clear()`
: Forgets the list and any remembered failure, so the next read asks Stripe.

`Catalogue.timeout()`
: The seconds a list is kept, from `STRIPE_CATALOGUE_TIMEOUT`.

The interface reaches the catalogue through `apps.get_app_config("mvp_payments_stripe").catalogue`
and never imports it.

## Asking whether a user is subscribed

`SubscriptionQuerySet` adds two methods to `Subscription.objects`, and to any queryset made from it.

`for_user(user)`
: The user's subscriptions, newest billing period first. It returns an empty queryset for someone
  who is not signed in and for a user who has not been saved, so it is safe to call with
  `request.user`.

`subscribed()`
: Only the subscriptions whose status is `active` or `trialing`. A subscription set to cancel at
  the end of its period still has one of those statuses until the period ends, so it counts.
  `past_due`, `unpaid`, `incomplete`, `incomplete_expired`, `paused`, `canceled`, and any status
  this version does not know, do not.

`current()`
: Every subscription that has not finished: every status except `canceled` and
  `incomplete_expired`, including any status this version does not know. This is what the user
  subscriptions page lists, so that a payment that has failed is shown and can be put right. It is
  not an answer to whether someone is subscribed.

```python
from mvp_payments.stripe.models import Subscription

Subscription.objects.for_user(request.user).subscribed().exists()  # True or False
Subscription.objects.for_user(request.user).subscribed().first()  # the current one, or None
```

A user with several subscriptions is subscribed when any one of them counts. What being subscribed
lets a user see is for your views to decide. See
[how to check whether a user is subscribed](../how-to/check-whether-a-user-is-subscribed.md).

## `Customer.sync()`

Every record is written by one method, `Customer.sync()`. It asks Stripe for the customer and for
all of the customer's subscriptions, whatever their status, and writes what comes back:

- A subscription Stripe returns is created, or updated in place by its Stripe identifier. Running
  `sync()` again with nothing changed at Stripe leaves the same rows.
- A subscription's price and billing period come from its first item. Stripe's checkout
  creates subscriptions with one item, and subscriptions with several are not supported.
- A subscription of the customer's that Stripe no longer returns is deleted.
- A subscription Stripe reports as ended stays, with the status Stripe gave it.
- A customer Stripe reports as deleted, or no longer has, is deleted here with its subscriptions.
  Nothing is changed on Stripe.
- A product's name is fetched from Stripe once per product, since Stripe will not include it in
  the subscription list.
- Any other error from Stripe, including Stripe being unreachable, is raised and leaves the
  records as they were.

The customer's row is locked while it runs, so two syncs of one customer take turns and the
later one writes the newer state.

```python
from mvp_payments.stripe.models import Customer

Customer.objects.get(stripe_id="cus_123").sync()
```

## The `stripe_sync` command

```bash
python manage.py stripe_sync
python manage.py stripe_sync --user ada
```

Runs `Customer.sync()` for every recorded customer, one after another, and prints how many it
synced. Run it after a period when webhooks did not arrive, such as a deploy, an expired signing
secret or a changed address. Running it again straight away changes nothing.

`--user`
: The `USERNAME_FIELD` value of one user, such as their username. Only that user's customer is
  synced. A name no user has, or a user with no recorded customer, stops the command with an
  error before Stripe is asked anything.

The command also clears the cached catalogue before it syncs, so the plans page reads Stripe
again, whether or not any customer is recorded.

A customer Stripe no longer has is removed with its subscriptions, as `sync()` does. Each customer
is synced in a transaction of its own. When Stripe cannot be asked, the command stops with an
error that says how many customers it had synced. Those stay synced, and running the command again
finishes the rest. The error names the kind of failure and never Stripe's message.

## The admin

Both models are registered in the Django admin, and both are read-only for everyone, a superuser
included. Nothing can be added, changed or deleted from their pages, and the bulk delete action is
not offered. Whether a staff user sees them at all follows Django's view permissions, so grant
`view_customer` and `view_subscription` to the staff who answer billing questions.

Subscriptions are listed with their Stripe ID, user, status, product name and period end. Filter
them by status, and search by the user's username or email address, the subscription's Stripe ID
or the customer's. A subscription's page shows the user, both Stripe identifiers, the status
exactly as stored, the price identifier, the amount with its currency (`1,500 JPY` for a
zero-decimal price, `20.00 USD` for two decimals), the billing interval, the period and whether
it cancels at its end. Customers are listed with their user, Stripe ID and creation time, and
searched the same way.

Deleting a user in the user admin still removes their customer and subscriptions with them, since
a deletion that cascades to a record asks that record's admin whether it may go. Only the app's own
delete pages are refused. Nothing is changed on Stripe.

The package does not mount the admin. Your project does, as it does for its own models.

## `Customer.erase()`

`customer.erase()` deletes the customer at Stripe, which cancels every subscription it has at
once, and then deletes the customer and its subscriptions here. A customer Stripe no longer has is
deleted here all the same. Any other error from Stripe, including Stripe being unreachable, is
raised as `stripe.StripeError` and changes nothing here. The error names the kind of failure and
never carries Stripe's message, which can repeat part of a key, so a project that logs it logs no
secret.

```python
from mvp_payments.stripe.models import Customer

Customer.objects.get(stripe_id="cus_123").erase()
```

## Personal data

`mvp_payments.stripe.personal_data` declares the app's records as
[django-mvp-compliance](https://github.com/django-mvp/django-mvp-compliance) kinds, for a project
that gives people a copy of their data and lets them delete their account. Nothing imports it
unless `MVP_COMPLIANCE_PERSONAL_DATA` names it, so django-mvp-compliance is not a dependency of
this package.

`StripeCustomer`
: The person's customer, as one record: `stripe_id` and `created`.

`StripeSubscriptions`
: Every subscription recorded for the person, ended ones included: `stripe_id`, `product_name`,
  `status`, `amount`, `currency`, `interval`, `interval_count`, `current_period_start`,
  `current_period_end`, `cancel_at_period_end` and `ended_at`.

Both kinds' `erase(user)` calls `Customer.erase()` on the person's customer, so deleting an
account deletes the customer at Stripe and fails as a whole when Stripe does not. See
[how to include a person's Stripe records in their data copy and account
deletion](../how-to/declare-the-stripe-records-to-django-mvp-compliance.md).

## `Customer.for_user()`

`Customer.for_user(user)` returns the user's customer, or `None` when they have none. It also
returns `None` for someone who is not signed in or not saved, so it is safe to call with
`request.user`.

## `Customer.client_reference()` and `Customer.from_checkout()`

A purchase is tied to a user only through the identity of the signed-in user, carried through
Stripe's checkout. Email addresses are never matched.

`Customer.client_reference(user)` returns the value every checkout the app starts carries as its
`client_reference_id`. It is the user's primary key and a signature of it, joined by `_`, so
it holds only letters, digits and underscores. The signature is made with your `SECRET_KEY` and a
salt of this app's own. A checkout started with someone else's primary key therefore ties
nothing to that person. A signature made before you rotated `SECRET_KEY` still verifies while the
old key is in `SECRET_KEY_FALLBACKS`, so a checkout open at the moment of the rotation is not lost. [ADR 0011](../adr/0011-a-checkout-is-tied-to-its-user-by-a-signed-reference.md)
records why.

```python
from mvp_payments.stripe.models import Customer

reference = Customer.client_reference(request.user)
```

`Customer.from_checkout(session_id)` retrieves a completed Checkout Session from Stripe and
returns the customer to sync, or `None`. It returns `None`, and records nothing, when:

- the session is not a subscription checkout, or has no customer;
- the reference is missing, is a bare primary key, or does not verify;
- the reference names a user who no longer exists;
- the user already has a different Stripe customer, or the session's customer is already recorded
  for another user. Both cases are logged as errors naming the identifiers and nothing else.

A user who subscribes again keeps the same customer, and the new subscription is recorded beside
the old one. The webhook and the return view can both tie the same first purchase at once. Whichever
records the customer second gets the row the first recorded.

## Handoffs to Stripe's own pages

Four views send a signed-in person to Stripe and bring them back. They are mounted with the
package's URLs under the same prefix as the webhook, and they exist only while `mvp_payments.stripe`
is in `INSTALLED_APPS`. Each needs a signed-in person and sends anyone else to the project's sign-in
page. The user subscriptions page links to them, and a project can too.

| View | URL name | Address | Method |
|---|---|---|---|
| `BillingPortalView` | `payments:stripe-billing-portal` | `stripe/billing-portal/` | POST |
| `PlanSwitchView` | `payments:stripe-plan-switch` | `stripe/plan-switch/` | POST |
| `BillingReturnView` | `payments:stripe-billing-return` | `stripe/return/` | GET |
| `CheckoutView` | `payments:stripe-checkout` | `stripe/checkout/` | POST |

`BillingPortalView` and `PlanSwitchView` answer with `{"url": ...}`, the address of a Stripe
billing-portal session for the person's customer, which a script follows. They answer:

| Answer | When |
|---|---|
| 200 | A portal session was created |
| 409 | The person has no Stripe customer, or, for the plan switch, nothing subscribed. Stripe is not asked and nothing is created |
| 429 | The person has opened the portal or the plan switch ten times in the current minute, the two counted together. Stripe is not asked |
| 502 | Stripe could not be asked or refused. The log names the kind of error and never Stripe's message |

`CheckoutView` is where a plan's Choose button posts, with the `price` chosen and a `return_to`
path on your site. It needs a signed-in person, answers only a POST, and keeps Django's CSRF check.
It checks the price against the catalogue, then calls `Customer.start_checkout()` and redirects the
reader to Stripe's checkout page. The session is a subscription for the price, with promotion codes
allowed and the person's signed reference attached. It is always for the person's own Stripe
customer. A person who has none has one made first, with their email address if the account has one,
so buying twice can never leave a paid subscription on a second customer the site does not know
([ADR 0015](../adr/0015-a-customer-is-made-before-the-first-checkout.md)). If Stripe no longer has
the customer, the app deletes its local copy, makes a new one and asks for the session again.

Whatever stops the checkout, the reader goes back to `return_to` with a message that
`mvp/base.html` shows above the page. A `return_to` that is not a path on your site is replaced by
the plans page.

| Case | What the reader gets |
|---|---|
| The catalogue cannot be read | An error message |
| The price is not on offer, or was not sent | A warning that the plan is no longer on offer |
| The person already holds the price | A redirect to the user subscriptions page |
| The person has started ten checkouts in the current minute | A warning to wait a moment. Stripe is not asked |
| Stripe refuses or cannot be reached | An error message. The log names the kind of error and never Stripe's message |

`Customer.start_checkout(user, price_id, success_url, cancel_url)` returns the address of the
Checkout Session and raises `stripe.StripeError` when Stripe cannot be asked. The view builds
`success_url` from the return view's absolute address with `?session_id={CHECKOUT_SESSION_ID}`
appended, so Stripe fills the session's id in.

Each of these creates something at Stripe for whoever posts, so each counts one person's requests
in the project's default cache and refuses them past ten a minute. CSRF keeps another site from
posting, but not the person themselves, and one account posting in a loop would otherwise spend
the Stripe account's rate limit for everyone. A shared cache counts across processes, a
local-memory one per process. The limits are `CheckoutView.rate_limit` and
`BillingPortalView.rate_limit`, each a `mvp_payments.stripe.limits.RateLimit`, which a subclass can
replace. A run of new accounts is not something one person's limit can stop: throttle sign-up for
that.

The portal view opens the portal's home. The plan-switch view opens the plan-change screen for the
person's subscription, or the portal's home when they have several. Both send the reader back
through the return view.

`BillingReturnView` runs `Customer.sync()` for the signed-in person's customer, so a change made in
the portal is already recorded, and redirects to the user subscriptions page with `?returned=1`. It
redirects whatever happens: a person with no customer and no `session_id` is not sent to Stripe,
and a Stripe failure is logged and leaves the page to wait for the webhook. It asks Stripe at most
once per person every `BillingReturnView.REFRESH_PAUSE` seconds (ten). Any page can make a browser
load it, and without the pause one account could spend the Stripe account's rate limit for
everyone. A return inside the pause redirects straight away and leaves the update to the webhook. A development server,
which Stripe cannot reach, relies on this to show a change at once.

Checkout sends the reader back here with `?session_id=` set to the Checkout Session. When the
person has no customer yet, the view ties the purchase to them with `Customer.from_checkout()`
before it syncs, so a first purchase shows at once and does not wait for the webhook. A session
made for another person ties nothing to this one.

The views are classes with hooks `is_offered(customer)` and `get_flow_data(customer, return_url)`,
so a project can subclass them.

On the customer, three more methods do the Stripe calls:

`Customer.make_for(user)`
: Makes a Stripe customer for a user who has none, with their email address when they have one,
  records it and returns it. When another request recorded one for the user first, that one is
  returned and the one just made is left on Stripe with nothing bought on it. Raises
  `stripe.StripeError` when Stripe cannot be asked, and records nothing.

`Customer.portal_url(return_url, flow_data=None)`
: Creates a billing-portal session and returns its address. Raises `stripe.StripeError` when
  Stripe cannot be asked.

`Customer.plan_change_flow(return_url)`
: The `flow_data` that opens the plan-change screen for the customer's one subscribed
  subscription, or `None` when they have none or more than one.

## The webhook

The address is `stripe/webhook/` under wherever you mounted the package's URLs, and its URL name
is `payments:stripe-webhook`. It exists only while `mvp_payments.stripe` is in `INSTALLED_APPS`.
The view is `mvp_payments.stripe.views.webhook`. It accepts POST and refuses every other method
with 405, and it needs no CSRF token.

The signature is verified with Stripe's own SDK before anything in the request is read. A request
that does not verify, including one signed with a secret you have since replaced, changes nothing.

A verified event is a reason to ask Stripe for the current state, not the state itself. A
subscription event, a deleted customer or a completed checkout makes the app call
`Customer.sync()` for the customer it concerns. The same event arriving twice, late, or after a
newer one about the same subscription therefore leaves the same records.

| Event | Customer synced |
|---|---|
| `checkout.session.completed` | The one `Customer.from_checkout()` returns |
| `customer.subscription.*` | The one whose `stripe_id` is the subscription's customer |
| `customer.deleted` | The one whose `stripe_id` is the deleted customer |
| Any other type | None |

A verified `product.*` or `price.*` event also calls `Catalogue.clear()`, so the next read of the
catalogue asks Stripe and the plans page shows the change. An event that does not verify clears
nothing. The clearing reaches the plans page only when the cache is shared across processes; see
[the catalogue](#the-catalogue).

| Answer | When |
|---|---|
| 400 | The signature is missing, wrong or expired, or the body is not a Stripe event |
| 500 | Stripe could not be asked, or `STRIPE_WEBHOOK_SECRET` is not set. Stripe sends the event again, and no record has changed |
| 200 | Everything else, including an event type the app does not keep and a customer that was never tied to a user |

Every answer has an empty body.

## Module names

These are importable but are not the app's interface. They are listed so that nothing public goes
undescribed.

`mvp_payments.stripe.client.http_client`
: `None` in normal use, so the app builds the SDK's `RequestsClient` with the configured timeout. A
  test sets it to a `stripe.HTTPClient` of its own to keep requests off the network.

`mvp_payments.stripe.client.TIMEOUT` and `MAX_NETWORK_RETRIES`
: The timeout used when `STRIPE_TIMEOUT` is not set, ten seconds, and the two retries every request
  gets.

`mvp_payments.stripe.limits.RateLimit(name, limit, seconds)`
: Counts one person's requests in fixed windows of `seconds`. `allows(user)` counts the request and
  says whether it is within `limit`.

`mvp_payments.stripe.models.from_epoch(seconds)`
: Turns a Stripe timestamp in epoch seconds into an aware UTC datetime, or `None` when Stripe
  reported none.

`mvp_payments.stripe.views.BillingPortalView`, `PlanSwitchView`, `BillingReturnView` and
`CheckoutView`
: The handoff views described above.

`mvp_payments.stripe.views.customer_for(event)`
: Finds the `Customer` a verified webhook event is about, or `None`.

`mvp_payments.stripe.models.logger` and `mvp_payments.stripe.views.logger`
: The modules' loggers, named after the module. They record error types and identifiers, never a
  secret or Stripe's message.
