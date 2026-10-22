# How to point Stripe at the webhook

The Stripe app learns of changes from Stripe's webhooks. Do this once the
[app is installed](install-the-stripe-app.md), so that a subscription made or changed on Stripe
reaches your database.

1. Mount the package's URLs once, as the README describes. The webhook comes with them, and only
   while `mvp_payments.stripe` is in `INSTALLED_APPS`. Mounted at `account/billing/`, its address
   is `account/billing/stripe/webhook/`.
2. In the Stripe Dashboard, under Developers, Webhooks, add an endpoint at that address on your
   site.
3. Send it these events:

   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `customer.subscription.paused`
   - `customer.subscription.resumed`
   - `customer.deleted`
   - `product.created`, `product.updated` and `product.deleted`
   - `price.created`, `price.updated` and `price.deleted`

4. Copy the endpoint's signing secret into `MVP_PAYMENTS["STRIPE_WEBHOOK_SECRET"]`.

Stripe now calls your site for each of those events. The customer events bring the records
into step, and the product and price events make the [plans page](../reference/plans-page.md)
read Stripe again, so a change made in the dashboard shows on the page. That only reaches the page
when your project's cache is shared across processes, as the
[catalogue reference](../reference/stripe-app.md#the-catalogue) explains. What the webhook
answers, and what it does with each event, is in the
[webhook reference](../reference/stripe-app.md#the-webhook).

If webhooks were missed, for example while the endpoint was down, bring the records back into step
with `python manage.py stripe_sync`. See the
[command reference](../reference/stripe-app.md#the-stripe_sync-command).
