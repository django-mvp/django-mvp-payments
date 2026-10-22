# How to check whether a user is subscribed

Use this in a view of your own once the [Stripe app is installed](install-the-stripe-app.md) and
its [webhook is pointed at your site](point-stripe-at-the-webhook.md). The app tells you whether
someone is subscribed. What that lets them see is up to your view.

1. Import the model:

   ```python
   from mvp_payments.stripe.models import Subscription
   ```

2. Ask for the signed-in user's subscriptions that count, and test them. A visitor who is not
   signed in has none, so no separate check is needed:

   ```python
   def members_page(request):  # "pricing" is your own pricing page
       if not Subscription.objects.for_user(request.user).subscribed().exists():
           return redirect("pricing")
       return render(request, "members.html")
   ```

3. When you need the subscription itself, its status, price or period, take the first one. The
   newest billing period comes first, and the answer is `None` when the user has none that counts:

   ```python
   current = Subscription.objects.for_user(request.user).subscribed().first()
   if current is not None:
       ends = current.current_period_end
   ```

Which statuses count, and why a subscription set to cancel at the end of its period still does, is
in the [reference](../reference/stripe-app.md#asking-whether-a-user-is-subscribed).
