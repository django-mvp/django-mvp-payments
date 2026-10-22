# Implementation Plan: Keep each user's Stripe subscription in the project's own database

**Branch**: `004-stripe-app` | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

## Summary

A Django app, `mvp_payments.stripe` (label `mvp_payments_stripe`), with two models, one webhook
view, one management command, a read-only admin and two system checks. Every path that changes
a record calls one method, `Customer.sync()`, which asks Stripe for the customer and all their
subscriptions and writes what comes back.

## Technical context

- Python 3.12+, Django 5.2 / 6.0 / 6.1, django-mvp ≥ 0.30.0
- New optional dependency: `stripe>=16,<17`, in the `stripe-lite` extra only
- Dev environment moves from `stripe<8` to the extra's range (research, finding 5)
- Storage: two tables, one migration

## Constitution check

| Article | How the plan meets it |
|---|---|
| XI, interface | Nothing under `mvp_payments/` outside `mvp_payments/stripe/` gains a model, an SDK import or a form. `mvp_payments/urls.py` includes the app's URLconf by dotted string when it is installed |
| XI, provider app | Records change only in `Customer.sync()` and `Customer.from_checkout()`, from what Stripe returns. The admin is read-only. The webhook verifies first and then fetches |
| XII | The SDK is declared only in `stripe-lite` and imported only under `mvp_payments/stripe/`. `tests/test_app.py` is rewritten to assert exactly that |
| XIII | The webhook is mounted by the include line a project already has, gated on `apps.is_installed("mvp_payments.stripe")` |
| XV | Amount stored as the minor-unit integer with its currency. Status stored as reported |
| XVI | `API_VERSION` constant passed to every client. The migration ships with the feature |
| IX | Every field has `verbose_name` and `help_text`. Index decisions below |
| VIII | Every user-facing string in models, admin and checks is wrapped with `gettext_lazy` |

## Layout

```text
mvp_payments/stripe/
├── __init__.py
├── apps.py            StripeConfig: name, label, verbose_name, default_auto_field; ready() imports checks
├── checks.py          E001 secret key missing, E002 webhook secret missing
├── client.py          API_VERSION and client(): StripeClient from settings
├── models.py          Customer, Subscription, SubscriptionQuerySet
├── views.py           webhook(request)
├── urls.py            stripe/webhook/ → webhook, name "stripe-webhook"
├── admin.py           CustomerAdmin, SubscriptionAdmin, read-only
├── management/commands/stripe_sync.py
└── migrations/0001_initial.py
docs/stripe.md         the app's how-to and reference (Diátaxis: one how-to and one reference section)
```

## Data model

**Customer** (`mvp_payments_stripe_customer`)

| Field | Type | Index | Why |
|---|---|---|---|
| `user` | `OneToOneField(AUTH_USER_MODEL, CASCADE, related_name="stripe_customer")` | unique | one per user, looked up by user |
| `stripe_id` | `CharField(255, unique=True)` | unique | every webhook looks the customer up by it |
| `created` | `DateTimeField(auto_now_add)` | none | shown in the admin only |

**Subscription** (`mvp_payments_stripe_subscription`)

| Field | Type | Index | Why |
|---|---|---|---|
| `customer` | `ForeignKey(Customer, CASCADE, related_name="subscriptions")` | FK | `for_user()` joins through it |
| `stripe_id` | `CharField(255, unique=True)` | unique | upsert key |
| `status` | `CharField(32, choices=Status)` | `db_index` | `subscribed()` and the admin filter on it |
| `price_id` | `CharField(255)` | none | displayed only |
| `product_name` | `CharField(255, blank=True)` | none | displayed only |
| `amount` | `BigIntegerField(null=True)` | none | minor unit; null for a price with no unit amount |
| `currency` | `CharField(3)` | none | lower-case ISO code as Stripe reports it |
| `interval` | `CharField(16)` | none | `day`, `week`, `month`, `year` |
| `interval_count` | `PositiveIntegerField(default=1)` | none | |
| `current_period_start` | `DateTimeField(null=True)` | none | |
| `current_period_end` | `DateTimeField(null=True)` | none | default ordering only, on a per-user set of one or two rows |
| `cancel_at_period_end` | `BooleanField(default=False)` | none | |
| `ended_at` | `DateTimeField(null=True)` | none | |
| `updated` | `DateTimeField(auto_now)` | none | admin only |

`Meta.ordering = ["-current_period_end"]`, so `.first()` is the latest.

`Subscription.Status`: `TextChoices` of Stripe's documented statuses (`incomplete`,
`incomplete_expired`, `trialing`, `active`, `past_due`, `canceled`, `unpaid`, `paused`).

## Behaviour

**`SubscriptionQuerySet`**

- `for_user(user)` — the user's subscriptions; `none()` for an anonymous or unsaved user.
- `subscribed()` — `status__in=("active", "trialing")`.

The documented answers are `Subscription.objects.for_user(user).subscribed().exists()` and
`.first()`. No other helper.

**`Customer.sync()`** — atomic, and its first statement locks this customer's row with
`select_for_update()`, so two webhooks for one customer cannot write an older state over a newer
one. Retrieve the customer from Stripe. Deleted or `resource_missing` → delete this row (its
subscriptions go with it) and return. Otherwise list the customer's subscriptions with
`status="all"`, auto-paging, with no expansion: Stripe refuses `data.items.data.price.product`
as more than four levels deep (sandbox call, 2026-10-22). Retrieve each distinct product named by
the first items' prices once, for its name, and `update_or_create` one row per subscription by
`stripe_id`. Rows for this customer that Stripe
did not return are deleted. Any other `StripeError` propagates.

**`Customer.client_reference(user)`** — classmethod. The value a page passes to the pricing table
as `client-reference-id`: the user's primary key and an HMAC of it, joined by `_`, built with
`django.utils.crypto.salted_hmac` under the app's own salt. The pricing table accepts only
letters, digits, dashes and underscores, which rules out `django.core.signing`'s separator. A
bare primary key would let anyone embed the public pricing table on a page of their own and tie
their purchase to another user.

**`Customer.from_checkout(session_id)`** — classmethod. Retrieve the checkout session. Not
`mode="subscription"`, or no `client_reference_id`, or no `customer` → return `None`. Split the
reference, check its HMAC with `constant_time_compare`, and find the user by the primary key;
a bad signature or no such user → `None`. User has no customer → create one
with the session's customer id. User has one with the same id → it. User has one with a
different id → log an error naming both, return `None`. Returns the customer to sync.

**`webhook(request)`** — `csrf_exempt`, `require_POST`. Verify with `stripe.Webhook.construct_event`
and the configured secret; `ValueError` or `SignatureVerificationError` → 400, nothing logged
beyond the error type. Then by `event.type`:

- `checkout.session.completed` → `Customer.from_checkout(event.data.object.id)`, then `sync()`
- `customer.subscription.*` → the `Customer` with `stripe_id=event.data.object.customer`, then `sync()`
- `customer.deleted` → the `Customer` with `stripe_id=event.data.object.id`, then `sync()`
- anything else, or no matching customer → 200

`StripeError` while handling → 500, so Stripe retries. Success → 200. The response body is empty
in every case.

**`stripe_sync` command** — `manage.py stripe_sync [--user <username>]`. Iterates customers
(one if named; unknown name → `CommandError`), calls `sync()` on each, reports the count. A
`StripeError` stops it with `CommandError` naming how many were synced; each customer's sync is
its own transaction, so those are kept.

**Admin** — both models registered; `has_add_permission` and `has_change_permission` return
`False`, `has_view_permission` is Django's. `has_delete_permission` returns `False` on the app's
own admin views and Django's answer elsewhere, so nothing here can be deleted from its own pages
while deleting a user from the user admin still removes their customer and subscriptions
(Django checks every cascaded model's delete permission, `django/contrib/admin/utils.py`,
`get_deleted_objects`). The `delete_selected` action is removed. `SubscriptionAdmin` sets
`list_select_related = ("customer__user",)`. Subscriptions:
`list_display` user, status, product name, period end; `list_filter` status;
`search_fields` the user's `USERNAME_FIELD` and email, and the Stripe ids.

**Checks** — registered from `StripeConfig.ready()`. Error when `MVP_PAYMENTS` lacks a non-empty
`STRIPE_SECRET_KEY` (E001) or `STRIPE_WEBHOOK_SECRET` (E002). The message names the setting and
never prints a value.

## Interface changes outside the app

- `mvp_payments/urls.py`: append `path("", include("mvp_payments.stripe.urls"))` when
  `apps.is_installed("mvp_payments.stripe")`.
- `pyproject.toml`: `[project.optional-dependencies] stripe-lite = ["stripe>=16,<17"]`; dev group
  takes `django-mvp-payments[stripe-lite]` in place of `stripe<8`; mypy files gain the app.
- `tests/test_app.py`: the interface rules are scoped to the package outside
  `mvp_payments/stripe/`; new assertions that the base requirements are Django and django-mvp
  only, that `stripe-lite` requires only `stripe`, and that no module outside the app imports
  it.
- Demo: add `mvp_payments.stripe` to `INSTALLED_APPS`, read `STRIPE_TEST_WEBHOOK_SECRET` from
  `demo/.env`, stop mounting `drf_stripe.urls`, pin the global `stripe.api_version` for the
  drf-stripe calls, and document `stripe listen --forward-to <base>/account/billing/stripe/webhook/`
  in `demo/.env.example` and the README's demo section.

## Testing approach

- `tests/stripe_fake.py`: a `stripe.HTTPClient` subclass holding canned Stripe objects keyed by
  method and path, installed by a fixture that builds the app's client with it. The SDK's request
  building and response parsing run for real. Our own code is never mocked.
- `tests/test_stripe/` mirrors `mvp_payments/stripe/`: `test_models.py`, `test_views.py`,
  `test_admin.py`, `test_checks.py`, `test_client.py`,
  `test_management/test_commands/test_stripe_sync.py`.
- Webhook requests are signed in tests with `hmac`, exactly as Stripe documents, so the real
  verification runs.
- Factories: `StripeCustomerFactory`, `StripeSubscriptionFactory` in `tests/factories.py`.
- Field contract: one parametrised test over every field for `verbose_name` and `help_text`.
- `makemigrations --check` clean.
- Secrets: render the admin pages, trigger each check and a failed webhook, and assert the
  configured secret strings appear in no response body and no captured log record (SC-008).

## Complexity tracking

| Addition | Why it is needed |
|---|---|
| `stripe` as an optional dependency | The provider's own SDK, for signature checks and API calls. Article XII allows it in the extra only |
| Two models and a migration | The feature is the local record (FR-003, FR-004) |
