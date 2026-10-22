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

The app is on while it is in `INSTALLED_APPS` and off when it is not. A project that installs the
extra but leaves the app out gets no tables, no pages and no URLs from it.

Next, [point Stripe at the webhook](point-stripe-at-the-webhook.md).
