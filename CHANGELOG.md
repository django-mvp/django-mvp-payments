# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
- The subscription page now renders what the signed-in person currently holds: six components
  (`<c-drf-stripe.subscription>`, `<c-drf-stripe.plan>`, `<c-drf-stripe.amount>`,
  `<c-drf-stripe.features>`, `<c-drf-stripe.portal-link>`, `<c-drf-stripe.no-subscription>`) and
  two names on its template context, `subscriptions` and `billing_portal_endpoint`, so a project
  overriding the template needs no view, context processor or query of its own.
  `docs/subscription-page.md` documents both.
- `MVP_PAYMENTS["DRF_STRIPE_BILLING_PORTAL"]`, telling the subscription page where a project
  mounted the backend's billing-portal endpoint (`customer-portal/`).
- `Page.in_navigation`, so a namespace can contribute a page that is routed and reverses without
  taking an entry in the Account Center's navigation.
- `<c-drf-stripe.plans-link>`, the control that leads to the plans page, and `plans_url` on the
  subscription page's template context.
- A page's view now receives its `Contribution` as well as its `Page`, so a page can address a
  sibling with `get_contribution().page_url(slug)` rather than a hard-coded URL name.

### Changed

- The drf-stripe namespace contributes one navigation entry, Subscription, under a **Billing**
  group, in place of three entries under a Payments group. The plans page is still there and is
  reached from a control on the subscription page.
- `<c-drf-stripe.portal-link>` now reads "Manage subscription" rather than "Manage billing", since
  no page is named for billing any more.

### Removed

- The drf-stripe billing page and its address (`payments:drf-stripe-billing`). It never had
  content, and what it was going to hold is the portal control that already sits on the
  subscription page.

- `mvp_payments` now goes **before** `mvp` in `INSTALLED_APPS`. The package ships its own copy of
  the Account Center's overview template and extends the name from inside it, which only resolves
  when this application is found first. The previous instruction would have left a project with
  navigation entries and no card, and nothing to explain why.
- A page here may have whatever view it needs, built on django-mvp's view classes, rather than only
  a template-rendering one. It still holds no state, decides nothing about money and reaches no
  payment provider.
