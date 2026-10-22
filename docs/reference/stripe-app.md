# Stripe app reference

`mvp_payments.stripe` keeps a small copy of each user's Stripe subscription in your project's
database. Stripe stays the source of truth: the app records who each user's Stripe customer is
and that customer's subscriptions, with their status, price and period, and refreshes the copy
from Stripe whenever Stripe reports a change. It adds no payment logic. Choosing a plan,
switching, cancelling and updating a card all happen on Stripe's own hosted pages.

To set it up, see [how to install the Stripe app](../how-to/install-the-stripe-app.md) and
[how to point Stripe at the webhook](../how-to/point-stripe-at-the-webhook.md).

## Settings

Both settings live in the `MVP_PAYMENTS` dictionary and are read only from there.

`STRIPE_SECRET_KEY`
: Your Stripe secret key, `sk_...` or `rk_...`. Required. Every call the app makes to Stripe is
  authorised with it.

`STRIPE_WEBHOOK_SECRET`
: The signing secret of the webhook endpoint Stripe sends events to, `whsec_...`. Required. Every
  webhook is verified against it.

Neither value appears in a template, a log message or an error page. The app also never reads or
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

A message names the setting. It never prints a value.

## The Stripe API version

Every call carries the API version the app is written against, `mvp_payments.stripe.client.API_VERSION`,
rather than your account's default. Changing your account's default version does not change what
the app receives.

## Records

Both tables carry the `mvp_payments_stripe` label.

### `Customer`

One row per user who has become a Stripe customer, tied to the user by `user` (reverse name
`stripe_customer`). Deleting the user deletes the customer and its subscriptions here. Nothing is
changed on Stripe.

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
- A subscription's price and billing period come from its first item. Stripe's pricing table
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

## `Customer.client_reference()` and `Customer.from_checkout()`

A purchase is tied to a user only through the identity of the signed-in user, carried through
Stripe's checkout. Email addresses are never matched.

`Customer.client_reference(user)` returns the value a page passes to Stripe's pricing table as
its `client-reference-id`. It is the user's primary key and a signature of it, joined by `_`, so
it holds only letters, digits and underscores. The signature is made with your `SECRET_KEY` and a
salt of this app's own. Embedding the public pricing table on another page with someone else's
primary key therefore ties nothing to that person. [ADR 0011](../adr/0011-a-checkout-is-tied-to-its-user-by-a-signed-reference.md)
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
the old one.

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
: `None` in normal use, so the SDK picks its own HTTP client. A test sets it to a
  `stripe.HTTPClient` of its own to keep requests off the network.

`mvp_payments.stripe.models.from_epoch(seconds)`
: Turns a Stripe timestamp in epoch seconds into an aware UTC datetime, or `None` when Stripe
  reported none.

`mvp_payments.stripe.views.customer_for(event)`
: Finds the `Customer` a verified webhook event is about, or `None`.

`mvp_payments.stripe.models.logger` and `mvp_payments.stripe.views.logger`
: The modules' loggers, named after the module. They record error types and identifiers, never a
  secret or Stripe's message.
