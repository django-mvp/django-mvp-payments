# How to install the Stripe app

`mvp_payments.stripe` keeps a copy of each user's Stripe subscription in your project's database,
refreshed from Stripe whenever Stripe reports a change. Install it when you want to ask "is this
user subscribed?" without calling Stripe.

1. Install the package with its `stripe-lite` extra, which brings in Stripe's own SDK and
   nothing else:

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
   runtime configuration rather than writing them into the file. Both are described in the
   [settings reference](../reference/stripe-app.md#settings).

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

To offer the plans page, add its URLs at the address you choose, beside the single include of
`mvp_payments.urls`:

```python
urlpatterns = [
    ...,
    path("account/billing/", include("mvp_payments.urls")),
    path("plans/", include("mvp_payments.plans_urls")),
]
```

The page is then at `/plans/`, reachable as `payments_plans:stripe-plans`, and open to every
visitor. It draws every recurring price in your Stripe account, so there is nothing else to
configure. See [the plans page](../reference/plans-page.md).

The list of plans is kept in your default cache for an hour, or for
`MVP_PAYMENTS["STRIPE_CATALOGUE_TIMEOUT"]` seconds. A change in Stripe's dashboard shows when it
expires. To show it sooner, [send Stripe's product and price events to the
webhook](point-stripe-at-the-webhook.md) and run `stripe_sync`, which both clear the list. They
run in other processes than the page, so they reach it only when your default cache is shared
across processes (Redis, Memcached, a database or a file cache), not a local-memory or dummy one.

The app is on while it is in `INSTALLED_APPS` and off when it is not. A project that installs the
extra but leaves the app out gets no tables, no pages and no URLs from it.

Next, [point Stripe at the webhook](point-stripe-at-the-webhook.md).
