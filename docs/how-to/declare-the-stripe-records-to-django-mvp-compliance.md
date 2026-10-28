# How to include a person's Stripe records in their data copy and account deletion

Use this when your project gives people a copy of their data and lets them delete their account
with [django-mvp-compliance](https://github.com/django-mvp/django-mvp-compliance), and the
[Stripe app is installed](install-the-stripe-app.md). Without it, a person's copy leaves out who
they are to Stripe and their subscriptions, and deleting their account removes those records here
but leaves the customer live on Stripe, still billing them.

`mvp_payments.stripe.personal_data` declares the Stripe app's two records as django-mvp-compliance
kinds. Nothing in this package imports that module unless your settings name it, so a project
without django-mvp-compliance never needs it installed.

## Steps

1. Set up django-mvp-compliance's copy of a person's data, as in its how-to *How to declare what
   your project holds about a person*.

2. Add the Stripe app's kinds to `MVP_COMPLIANCE_PERSONAL_DATA`, after your own:

   ```python
   # settings.py
   MVP_COMPLIANCE_PERSONAL_DATA = [
       "accounts.personal_data.Profile",
       "datasets.personal_data.Datasets",
       "mvp_payments.stripe.personal_data.StripeCustomer",
       "mvp_payments.stripe.personal_data.StripeSubscriptions",
   ]
   ```

   List them last. Deleting a customer at Stripe cannot be undone, so every kind that might
   refuse its deletion should have its turn first.

3. Run `python manage.py check`. Both kinds say how they are deleted, so they never hold back
   django-mvp-compliance's **Delete account** page. Your own kinds still have to.

## What a person's copy holds

`StripeCustomer`
: The person's Stripe customer, as one record: its Stripe ID and when it was first recorded
  here. Empty for a person who never started a checkout.

`StripeSubscriptions`
: Every subscription the app has recorded for them, ended ones included, as Stripe last reported
  it: the Stripe ID, product name, status, amount and currency, billing interval, current period,
  whether it cancels at the period's end, and when it ended. `amount` is in the currency's minor
  unit, as the app stores it.

## What deleting the account does

Either kind's `erase` calls [`Customer.erase()`](../reference/stripe-app.md#customererase) on the
person's customer. It deletes the customer at Stripe, which cancels every subscription it has at
once, with no further charge. Once Stripe has reported the customer deleted, the customer and its
subscriptions are deleted here. The second kind then finds no customer and asks Stripe nothing.

A customer Stripe no longer has counts as deleted. Any other answer, including Stripe being
unreachable, raises `stripe.StripeError`. django-mvp-compliance then deletes nothing, the person
keeps their account and sees that it could not be deleted, and they can try again. A person is
never left without an account while Stripe goes on billing them.

If a step after the Stripe kinds fails, including the deletion of the account itself, the
account stays and the customer is already gone at Stripe. Nothing is billed. The records here
come back with the rest of the rolled-back deletion, and are removed when Stripe's webhook for
the deleted customer arrives, or the next time `stripe_sync` runs.
