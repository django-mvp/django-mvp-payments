# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Build pipeline, test harness and demo project.
- The URL configuration a project includes once (`mvp_payments.urls`), and the drf-stripe
  namespace's three pages — subscription, plans and billing — arriving in django-mvp's Account
  Center navigation when the backend is installed.
- A card for each installed backend on the Account Center's overview, leading into that backend's
  first page.
- A test suite guarantee that a second namespace leaves the first one's navigation entries, card
  and page addresses unchanged, and that no two declared namespaces can share a URL name.
- `docs/namespaces.md`, covering what a namespace declares and how to add one, and the first two
  architecture decision records.

### Changed

- `mvp_payments` now goes **before** `mvp` in `INSTALLED_APPS`. The package ships its own copy of
  the Account Center's overview template and extends the name from inside it, which only resolves
  when this application is found first. The previous instruction would have left a project with
  navigation entries and no card, and nothing to explain why.
- A page here may have whatever view it needs, built on django-mvp's view classes, rather than only
  a template-rendering one. It still holds no state, decides nothing about money and reaches no
  payment provider.
