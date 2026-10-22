# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Django 6.1 is supported, and tested on every change alongside 5.2 and 6.0.
- Build pipeline, test harness and demo project.
- The URL configuration a project includes once (`mvp_payments.urls`), and the drf-stripe
  namespace's pages arriving in django-mvp's Account Center when the backend is installed, under a
  labelled section of their own.
- A card for each installed backend on the Account Center's overview, leading into that backend's
  first page.
- A test suite guarantee that a second namespace leaves the first one's navigation entries, card
  and page addresses unchanged, and that no two declared namespaces can share a URL name.
- `docs/namespaces.md`, covering what a namespace declares and how to add one, and the first two
  architecture decision records.
- The user subscriptions page now renders what the signed-in person currently holds: six components
  (`<c-drf-stripe.subscription>`, `<c-drf-stripe.plan>`, `<c-drf-stripe.amount>`,
  `<c-drf-stripe.features>`, `<c-drf-stripe.portal-link>`, `<c-drf-stripe.no-subscription>`) and
  two names on its template context, `subscriptions` and `billing_portal_endpoint`, so a project
  overriding the template needs no view, context processor or query of its own.
  `docs/reference/user-subscriptions-page.md` documents both.
- `MVP_PAYMENTS["DRF_STRIPE_BILLING_PORTAL"]`, telling the user subscriptions page where a project
  mounted the backend's billing-portal endpoint (`customer-portal/`).
- `Page.in_navigation`, so a namespace can contribute a page that is routed and reverses without
  taking an entry in the Account Center's navigation.
- `<c-drf-stripe.plans-link>`, the control that leads to the plans page, and `plans_url` on the
  user subscriptions page's template context.
- A page's view now receives its `Contribution` as well as its `Page`, so a page can address a
  sibling with `get_contribution().page_url(slug)` rather than a hard-coded URL name.
- The plans page now mounts the provider's own pricing table with `<c-drf-stripe.pricing-table>`,
  configured by two settings, `MVP_PAYMENTS["DRF_STRIPE_PRICING_TABLE_ID"]` and
  `MVP_PAYMENTS["DRF_STRIPE_PUBLISHABLE_KEY"]`. `docs/reference/plans-page.md` documents the component, the
  two settings, and how to replace either the component or the page with your own.
- The pricing table carries the signed-in person's email address, so a purchase reaches the
  account that made it — the backend matches a customer to a user by address and reads no other
  identifier. An address passed as an attribute wins; where there is neither, the attribute is
  omitted rather than sent empty.
- `<c-drf-stripe.plans-unavailable>`, and the plans page's two ways of saying there is nothing to
  show: the sentence it renders when either setting is missing, and a message revealed in the
  browser when the provider's library never arrived. Both are translatable, and neither leaves a
  reader looking at empty space.
- `MVP_PAYMENTS["DRF_STRIPE_PLAN_SWITCH"]`, naming an endpoint of the project's own that opens the
  provider's plan-change screen for a subscriber's existing subscription. "Switch plans" posts to
  it. `docs/reference/user-subscriptions-page.md` says what the endpoint does, and the demo has a working one.
- `<c-drf-stripe.already-subscribed>`, shown on the plans page to somebody who already has a
  subscription, with a link to their user subscriptions page.
- A reader who comes back from paying at the provider to the user subscriptions page with `?returned=1`
  on the address is told their payment is being confirmed while the backend catches up, never that
  they have no subscription. The page's subscription region polls for itself with htmx every three
  seconds until the subscription appears, up to five times, then says to reload later. New:
  `<c-drf-stripe.provider-return>` and the page's `provider_return` context name.
- `mvp_payments.stripe`, an app that keeps each user's Stripe customer and subscriptions in your
  database. Add it to `INSTALLED_APPS` and install the `stripe-lite` extra (`stripe>=16,<17`). It
  verifies Stripe's webhooks, then fetches the current state from Stripe, against Stripe API
  version `2026-09-30.endive`, whatever your account's default is. It needs
  `MVP_PAYMENTS["STRIPE_SECRET_KEY"]` and `MVP_PAYMENTS["STRIPE_WEBHOOK_SECRET"]`, and a system
  check names whichever is missing without printing a value. Your views ask
  `Subscription.objects.for_user(user).subscribed()`. `python manage.py stripe_sync` re-syncs
  every recorded customer, or one with `--user`, after webhooks were missed. Its admin pages are
  read-only for everyone, a superuser included. The demo documents forwarding a sandbox's
  webhooks to it with `stripe listen`.
- The Stripe app mounts the handoffs to Stripe's own pages with the package's URLs:
  `payments:stripe-billing-portal` opens the billing portal, `payments:stripe-plan-switch` opens the
  plan-change screen, and `payments:stripe-billing-return` is where the portal sends the reader
  back, after running `Customer.sync()` for them. A person with no Stripe customer, or with nothing
  subscribed for the plan switch, is refused with 409. `Customer.for_user()`, `Customer.portal_url()`,
  `Customer.plan_change_flow()` and `Customer.pricing_table_client_secret()` back them.
- The plans page is open to every visitor. For a signed-in person it passes the pricing table
  `client-reference-id`, and for one who already has a Stripe customer also
  `customer-session-client-secret`, so a further purchase lands on the customer they have.
  `<c-stripe.pricing-table>` takes `client_reference_id` and `customer_session_client_secret`, and
  drops `customer-email` when a customer session is passed. A visitor who is not signed in is told
  to sign in first by the new `<c-stripe.sign-in-notice>`; a purchase made without signing in is
  tied to nobody. New context names: `client_reference_id`, `customer_session_client_secret` and
  `sign_in_url`.
- `Page.login_required`, so a namespace can contribute a page open to everyone. It defaults to
  `True`.
- The user subscriptions page lists every subscription a person currently holds, where it could show only
  those the former backend called current. [ADR 0012](docs/adr/0012-the-plans-page-is-open-to-everyone.md)
  records why the plans page is open.

### Changed

- "Manage subscription" and "Switch plans" send the current CSRF token from Django's cookie rather
  than the one the page was rendered with, so a page left open while the person signed out and
  back in still works. When the request is refused anyway, the control says the page is out of date
  and to reload it, instead of "try again later".
- The package is built with hatchling instead of poetry-core, and developed with uv instead of
  Poetry. The wheel contains the same files as before. The source distribution does too, plus the
  repository's `.gitignore`, which hatchling includes so that a build from it leaves out the same
  files.
- Requires django-mvp 0.30.0 or later, where it required 0.27.0. Two things in its upgrade
  reach a project using this package:
  - django-filter is now one of django-mvp's dependencies, so add `"django_filters"` to
    `INSTALLED_APPS`.
  - An alert no longer picks its icon from its variant. The alerts this package draws while a
    payment is being confirmed now name their icon. An alert of yours that relied on its
    variant's icon needs `icon="info"`, `icon="warning"`, `icon="error"` or `icon="success"`.

  See django-mvp's own changelog for the rest of what its upgrade asks of a project.
- Requires django-mvp 0.27.0 or later, where it required 0.24.0. The package's templates use
  django-mvp's page, card, data-field and empty-state components, which 0.27.0 moved under the
  `mvp.` prefix (`<c-mvp.page>`, `<c-mvp.card>`), and the old names no longer resolve. A template
  of yours that replaces one of the shipped pages needs the same rename. See django-mvp's own
  changelog for the settings its upgrade asks of a project: `daisy_cotton` directly below `mvp` in
  `INSTALLED_APPS`, the `mvp_forms` form pack in place of `crispy_tailwind`, and `mvp.urls`
  included at the site root.
- From django-mvp 0.25.0 the Account Center's navigation is drawn once, in the sidebar, and only
  on a page that navigation has an entry for. The user subscriptions page has an entry and shows it. The
  plans page has none, so it is drawn inside the Account Center's layout with the project's own
  sidebar.
- The demo now signs in and out through django-mvp's own
  development pages (`LOGIN_URL = "account_login"`) in place of Django's, which fixes its sign-out
  control. That control is drawn only when `account_logout` resolves, and Django's logout view
  refuses the plain link a project without it would need.
- **A subscriber no longer sees the pricing table.** It cannot show which plan they are on, and
  buying from it started a second subscription beside the first. The plans page now sends them to
  their user subscriptions page, and "Switch plans" there opens the provider's plan-change screen instead
  of linking to the plans page. Without `DRF_STRIPE_PLAN_SWITCH`, a subscriber is offered no switch
  control. `<c-drf-stripe.plans-link>` takes a new `switch_endpoint` attribute.
- `<c-drf-stripe.no-subscription>` says one thing, "You don't have an active subscription.", in
  place of a heading and a sentence that repeated it.
- A price synchronised by the backend on Python 3.12 or later shows its billing frequency in words.
  The backend stores `RecurringInterval.MONTH_1` there instead of `month_1`, and the frequency was
  shown as that raw text.

- The rule forbidding a publishable key to be read from Django settings now applies to a
  component rather than to the whole package. A page this package ships may read it and pass it
  to a component as an attribute; a component still never reads it. Without that distinction a
  shipped, configurable page could not exist, because every project would have to build and route
  the page itself to supply the attribute.
- The drf-stripe namespace contributes one navigation entry, Subscription, under a **Billing**
  group, in place of three entries under a Payments group. The plans page is still there and is
  reached from a control on the user subscriptions page.
- `<c-drf-stripe.portal-link>` now reads "Manage subscription" rather than "Manage billing", since
  no page is named for billing any more. It sits in a row beside the way to the plans page rather
  than beneath it.
- **Addresses no longer carry the backend's name.** A page is at `<your prefix>/subscription/`
  where it was at `<your prefix>/drf-stripe/subscription/`. Which library a project chose to talk
  to its payment provider has no business in an address a person reads, and URL *names* still
  carry the namespace, so nothing about collision safety changes. The demo now mounts the package
  at `account/billing/`, inside the Account Center's own prefix.
- `mvp_payments` now goes **before** `mvp` in `INSTALLED_APPS`. The package ships its own copy of
  the Account Center's overview template and extends the name from inside it, which only resolves
  when this application is found first. The previous instruction would have left a project with
  navigation entries and no card, and nothing to explain why.
- A page here may have whatever view it needs, built on django-mvp's view classes, rather than only
  a template-rendering one. It still holds no state, decides nothing about money and reaches no
  payment provider.
- **The `drf-stripe` namespace is now `stripe`, and its pages read `mvp_payments.stripe`.** Install
  the app and the `stripe-lite` extra; the namespace is contributed when `mvp_payments.stripe` is in
  `INSTALLED_APPS`. Rename `<c-drf-stripe.*>` to `<c-stripe.*>`, `cotton/drf_stripe/` to
  `cotton/stripe/`, `mvp_payments/drf_stripe/` template names to `mvp_payments/stripe/`, the static
  files under `mvp_payments/drf_stripe/` to `mvp_payments/stripe/`, and `payments:drf-stripe-*` URL
  names to `payments:stripe-*`. There are no aliases for the old names.
- **The settings keys are renamed.** `MVP_PAYMENTS["DRF_STRIPE_PRICING_TABLE_ID"]` is
  `MVP_PAYMENTS["STRIPE_PRICING_TABLE_ID"]`, and `DRF_STRIPE_PUBLISHABLE_KEY` is
  `STRIPE_PUBLISHABLE_KEY`.
- **A subscriber sees the pricing table again**, and the plans page no longer sends a visitor who
  is not signed in to sign in.
- `CurrentSubscription` carries the plan's name, amount and interval directly, one subscription
  being one price in the Stripe app. A subscription counts as current when the app counts it as
  subscribed, which a past-due one does not.
- "Switch plans" opens the portal's home, instead of a plan-change screen, for a person with several
  subscriptions.

### Removed

- The drf-stripe billing page and its address (`payments:drf-stripe-billing`). It never had
  content, and what it was going to hold is the portal control that already sits on the
  user subscriptions page.
- `drf-stripe-subscription` as a development dependency, and with it everything that read its
  records: `MVP_PAYMENTS["DRF_STRIPE_BILLING_PORTAL"]` and `MVP_PAYMENTS["DRF_STRIPE_PLAN_SWITCH"]`
  (the pages link to the Stripe app's own views), the demo's portal, plan-switch and return views,
  and the global `stripe.api_version` pin in the demo.
- `<c-stripe.plan>`, `<c-stripe.features>` and `<c-stripe.already-subscribed>`, and the plan
  features on the user subscriptions page, which the Stripe app does not record. A plan's quantity is
  not shown either.
