# The Stripe app

`mvp_payments.stripe` keeps a small copy of each user's Stripe subscription in your project's
database. Stripe stays the source of truth: the app records who each user's Stripe customer is
and that customer's subscriptions, with their status, price and period, and refreshes the copy
from Stripe whenever Stripe reports a change. It adds no payment logic. Choosing a plan,
switching, cancelling and updating a card all happen on Stripe's own hosted pages.

## How to install the Stripe app

1. Install the package with its `stripe-lite` extra, which brings in Stripe's own SDK and nothing
   else:

   ```bash
   pip install "django-mvp-payments[stripe-lite]"
   ```

2. Add the app to `INSTALLED_APPS`:

   ```python
   INSTALLED_APPS = [
       ...,
       "mvp_payments",
       "mvp_payments.stripe",
       "mvp",
   ]
   ```

3. Put your Stripe secret key and webhook signing secret in your settings, taking them from
   runtime configuration rather than writing them into the file:

   ```python
   import os

   MVP_PAYMENTS = {
       "STRIPE_SECRET_KEY": os.environ["STRIPE_SECRET_KEY"],
       "STRIPE_WEBHOOK_SECRET": os.environ["STRIPE_WEBHOOK_SECRET"],
   }
   ```

4. Create the tables:

   ```bash
   python manage.py migrate
   ```

5. Run the project's checks. A missing setting is reported by name:

   ```bash
   python manage.py check
   ```

The app is on when it is in `INSTALLED_APPS` and off when it is not. A project that installs the
extra but leaves the app out gets no tables, no pages and no URLs from it.

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
