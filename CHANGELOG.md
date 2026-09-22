# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Build pipeline, test harness and demo project.
- The URL configuration a project includes once (`mvp_payments.urls`), and the drf-stripe
  namespace's three pages — subscription, plans and billing — arriving in django-mvp's Account
  Center when the backend is installed, under a labelled section of their own.
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
- The plans page now mounts the provider's own pricing table with `<c-drf-stripe.pricing-table>`,
  configured by two settings, `MVP_PAYMENTS["DRF_STRIPE_PRICING_TABLE_ID"]` and
  `MVP_PAYMENTS["DRF_STRIPE_PUBLISHABLE_KEY"]`. `docs/plans-page.md` documents the component, the
  two settings, and how to replace either the component or the page with your own.
- The pricing table carries the signed-in person's email address, so a purchase reaches the
  account that made it — the backend matches a customer to a user by address and reads no other
  identifier. An address passed as an attribute wins; where there is neither, the attribute is
  omitted rather than sent empty.
- `<c-drf-stripe.plans-unavailable>`, and the plans page's two ways of saying there is nothing to
  show: the sentence it renders when either setting is missing, and a message revealed in the
  browser when the provider's library never arrived. Both are translatable, and neither leaves a
  reader looking at empty space.

### Changed

- The rule forbidding a publishable key to be read from Django settings now applies to a
  component rather than to the whole package. A page this package ships may read it and pass it
  to a component as an attribute; a component still never reads it. Without that distinction a
  shipped, configurable page could not exist, because every project would have to build and route
  the page itself to supply the attribute.

- `mvp_payments` now goes **before** `mvp` in `INSTALLED_APPS`. The package ships its own copy of
  the Account Center's overview template and extends the name from inside it, which only resolves
  when this application is found first. The previous instruction would have left a project with
  navigation entries and no card, and nothing to explain why.
- A page here may have whatever view it needs, built on django-mvp's view classes, rather than only
  a template-rendering one. It still holds no state, decides nothing about money and reaches no
  payment provider.
