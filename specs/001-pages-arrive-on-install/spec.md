# Feature Specification: Payment pages that appear when you install a backend

**Feature Branch**: `001-pages-arrive-on-install`

**Created**: 2026-09-21

**Status**: Draft

**Serves**: G1 (adding a backend to a project takes minimal setup and no page-building), G3 (one backend's pages never affect another's)

**Roadmap**: R1 — Pages that arrive on their own

**Issue**: #6

**Input**: A host project that installs this package alongside a payment backend should get that backend's pages in the Account Center straight away, without writing a view, a template or a menu entry of its own. Which backends are installed is what decides what appears: install one and its pages are there, leave it out and nothing from it is, and the project carries none of that backend's dependencies either. A person should never be offered a link that goes nowhere, and adding a second backend later should leave the first one's pages exactly as they were.

## Clarifications

### Session 2026-09-21

Five ambiguities were found by the coverage scan and answered from the intake discussion, the
project's standards document and its README. Longer rationale is in `decisions.md`.

- **Q: What does a contributed page show before the feature that fills it has been built?**
  A: The page's own title and heading inside the Account Center layout, and nothing else. No
  placeholder copy, no notice that something is coming. The pages exist so that the arrival
  mechanism is real and so that each later feature fills a page rather than also routing one, and
  the release gate for this stage is explicitly pre-viable with nothing published. Copy written to
  apologise for an empty page would be written to be deleted. Recorded as FR-007.

- **Q: Does a contributed page require a signed-in person, and what happens to a visitor who is
  not signed in?**
  A: It requires one, and an anonymous visitor is sent to the project's sign-in page, the same way
  the Account Center's own landing page behaves. Anything finer than that — who among the signed-in
  people may see which page — is the host project's to enforce in its own configuration, because
  this package holds no entitlement information and must not appear to be making an access
  decision. Recorded as FR-008.

- **Q: Do a backend's entries sit directly in the Account Center navigation, or under a group of
  their own?**
  A: Under a group, labelled for what the group contains rather than for the library behind it —
  "Payments" for the first namespace. This was first settled the other way, on the reasoning that
  the only honest label for a group was the name of a Python library. Using the running pages
  answered it: the Account Center is shared with whatever else a project installed, and
  django-accounts-center already sections its own part of the same menu under "Email &
  Authentication". A namespace declares its own group label, so nothing here reaches across
  namespaces. Recorded as FR-005.

- **Q: How many cards does an installed backend put on the Account Center overview?**
  A: Exactly one, whatever number of pages it contributes. The overview is a summary and a way in,
  so one card per backend leads to that backend's pages. A card per page would reproduce the
  navigation that is already drawn beside it. Recorded as FR-006.

- **Q: Only one payment backend exists to test against. How is "a second backend changes nothing
  about the first" established?**
  A: With a second namespace defined inside the test suite, contributing through the same mechanism
  as the real one. The claim under test is that two contributions are independent, and a second
  contribution is all that needs to exist for that to be answerable. Recorded in Assumptions and
  exercised by User Story 5.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The backend's pages are simply there (Priority: P1)

Someone is building a Django project on django-mvp. They have chosen a payment backend, installed
it and configured it. They install this package, add it to their installed applications and add one
line to their URL configuration. They sign in, open the Account Center, and the backend's pages are
in its navigation. They click one and land on it. They wrote no view, no template and no menu entry.

**Why this priority**: This is the feature. Everything else here qualifies it — what happens when
the backend is absent, what the overview shows, what happens to a page that cannot be reached.
Without this slice the package is a directory of templates to copy out of.

**Independent Test**: Install the package and the backend in a project, mount the URL
configuration, sign in and open the Account Center. The backend's entries are in the navigation and
each one leads to a page that renders.

**Acceptance Scenarios**:

1. **Given** a project with this package and a payment backend installed, and this package's URL
   configuration mounted once, **When** a signed-in person opens the Account Center, **Then** the
   backend's pages appear in its navigation, under one group labelled for that namespace.
2. **Given** that same project, **When** the person follows one of those entries, **Then** the
   corresponding page renders inside the Account Center layout.
3. **Given** that same project, **When** its source is examined, **Then** it contains no view,
   template or menu entry belonging to those pages, and exactly one line mounting this package.
4. **Given** that same project, **When** someone who is not signed in requests one of those pages
   directly, **Then** they are sent to the project's sign-in page.

---

### User Story 2 - A backend you have not installed costs you nothing (Priority: P1)

The same person has not chosen a payment backend yet, or has chosen a different one. They install
this package anyway, because something else in their stack brought it in. Nothing appears anywhere,
nothing breaks, and their project has not acquired that backend's dependencies.

**Why this priority**: The other half of the promise, and the one that makes the first half safe to
rely on. A package that contributes pages for a backend that is not installed puts a broken link in
front of a person, and a package that pulls a backend in to be sure hands every project the
backend's own constraints.

**Independent Test**: Install the package without the backend, sign in and open the Account Center.
Nothing from the backend appears. Read the package's declared dependencies and its imports.

**Acceptance Scenarios**:

1. **Given** a project with this package installed and no payment backend, **When** a signed-in
   person opens the Account Center, **Then** no entry, card or page belonging to any backend
   appears.
2. **Given** that same project, **When** the package's declared runtime dependencies are read,
   **Then** they are exactly Django and django-mvp.
3. **Given** that same project, **When** the package's own code is read, **Then** no module imports
   a payment backend or a payment provider's library.
4. **Given** a project that installs the backend after the fact, **When** it is added to the
   installed applications and nothing else changes, **Then** its pages appear.

---

### User Story 3 - The overview says what is available (Priority: P2)

The person lands on the Account Center's overview rather than going straight to a page. Each
installed backend has put a card there, and the card is the way into that backend's pages.

**Why this priority**: The overview is where a person arrives by default, so a backend that
contributes only navigation entries is discoverable only to someone already looking for it. It is
second because the pages are reachable without it.

**Independent Test**: With the backend installed, open the Account Center overview and confirm one
card for that backend leading to its pages.

**Acceptance Scenarios**:

1. **Given** a project with the backend installed, **When** a signed-in person opens the Account
   Center overview, **Then** one card for that backend is on it.
2. **Given** the same project with the backend removed from its installed applications, **When**
   the person opens the overview, **Then** the card is gone and the overview renders without it.

---

### User Story 4 - Nothing is offered that cannot be reached (Priority: P3)

The person's project has the backend installed but has not mounted this package's URL
configuration. The Account Center opens normally. No entry leads nowhere, and nothing raises.

**Why this priority**: A dead link is worse than an absent one, and mounting the URL configuration
is the single step that cannot be made automatic. It is third because it is a degraded state rather
than the working one.

**Independent Test**: Install the package and the backend, leave the URL configuration unmounted,
sign in and open the Account Center.

**Acceptance Scenarios**:

1. **Given** a project with the package and backend installed and the URL configuration not
   mounted, **When** a signed-in person opens the Account Center, **Then** the page renders, neither
   the backend's group nor any entry in it appears, and no error is raised.
2. **Given** that same project, **When** the URL configuration is mounted, **Then** the entries
   appear without any other change.

---

### User Story 5 - A second backend leaves the first alone (Priority: P3)

A second namespace is added to the package. Everything the first namespace contributes stays exactly
as it was, and neither one can reach the other's pages.

**Why this priority**: This is the separation the package's design rests on, and the point at which
it stops being an intention. It is third because there is one backend today, so the guarantee is
about the shape of what is built rather than about something a person can see now.

**Independent Test**: Add a second namespace contributing through the same mechanism and compare
the first namespace's entries, card and pages before and after.

**Acceptance Scenarios**:

1. **Given** a project with one namespace's backend installed, **When** a second namespace's
   backend is installed alongside it, **Then** the first namespace's entries, card and pages are
   unchanged.
2. **Given** both installed, **When** each namespace's pages are examined, **Then** neither
   resolves to the other's page or reuses the other's URL name.

### Edge Cases

- A project mounts the URL configuration but installs no backend: the mounted paths exist and
  contribute nothing, and the Account Center renders as it did before.
- A backend is installed but its own URL configuration is not mounted, so its HTTP endpoints are
  absent: the pages still arrive, because arrival depends on installation alone. What a page does
  with an unreachable endpoint belongs to the feature that fills the page.
- Someone who is not signed in requests a contributed page's address directly: they are sent to the
  project's sign-in page.
- A project removes a backend from its installed applications while people are using it: the
  entries, card and pages disappear on the next request, and the addresses stop resolving.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST expose a URL configuration a project includes once, at a prefix of
  the project's choosing, and MUST require no other wiring in that project.
- **FR-002**: A namespace MUST contribute its entries, card and pages when the backend it speaks to
  is in the project's installed applications, and MUST contribute nothing otherwise. There MUST be
  no setting, flag or registry that turns a contribution on or off.
- **FR-003**: Contributions MUST be registered when the application is ready. No module in this
  package may inspect the application registry, reverse a URL or read project configuration while
  the framework is still starting.
- **FR-004**: The package MUST declare no payment backend among its dependencies and MUST import
  none. Where a page needs a backend's records, it MUST reach them through the application registry
  rather than by importing the backend.
- **FR-005**: An installed backend's pages MUST appear in the Account Center's navigation as one
  group, labelled by the namespace that declares them. A group whose pages cannot be reached MUST
  NOT be shown.
- **FR-006**: An installed backend MUST contribute exactly one card to the Account Center's
  overview, leading to that backend's pages.
- **FR-007**: The drf-stripe namespace MUST contribute three pages — the person's subscription, the
  plans available to them, and their billing management — each reachable from its own navigation
  entry, each rendering its title and heading inside the Account Center layout. What each page shows
  beyond that is delivered by later features.
- **FR-008**: A contributed page MUST require a signed-in person and MUST send anyone else to the
  project's sign-in page. The package MUST make no finer access decision than that.
- **FR-009**: An entry whose page cannot be reached MUST NOT be shown.
- **FR-010**: One namespace's contribution MUST NOT alter or remove another namespace's entries,
  card or pages, and MUST NOT share a URL name with one.
The last three apply across every story rather than to any one of them.

- **FR-011**: Every string a person reads in an entry, a card or a page MUST be translatable.
- **FR-012**: The package's documentation MUST state the one line a project adds, and what appears
  as a result of adding it.
- **FR-013**: The project's standards document and its README MUST be corrected where they state
  that the package ships only template-rendering views, and the superseded working-notes document
  and the reference to it MUST be removed.

### Key Entities

- **Contribution**: everything a namespace puts into the Account Center when its backend is
  installed — its navigation entries, its overview card and its pages. A contribution is made or not
  made as a whole, and belongs to exactly one namespace.
- **Namespace**: the backend a set of components speaks to, and the name that set is grouped under.
- **Page set**: the pages one namespace contributes. For drf-stripe, three.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A project that installs this package and a backend and adds one line to its URL
  configuration can reach every page that backend contributes, having written no view, template or
  menu entry.
- **SC-002**: Removing the backend from the installed applications removes all three pages, every
  entry and the card, leaving nothing behind and raising nothing.
- **SC-003**: The package's declared runtime dependencies are exactly Django and django-mvp, and no
  module in it imports a payment backend or a payment provider's library.
- **SC-004**: With the backend installed and the URL configuration unmounted, the Account Center
  renders with no entry that leads nowhere.
- **SC-005**: Adding a second namespace changes nothing about the first namespace's entries, card or
  pages, and neither namespace's addresses resolve to the other's pages.
- **SC-006**: Every page, entry and card is exercised by a test that asserts what is rendered rather
  than which classes are present.

## Assumptions

- The pages this feature contributes arrive before they have content. Each one is filled by a later
  roadmap item: the subscription page by R2, the plans page by R3, billing management by R5.
- The demo project installs the real backend, as a development dependency, and its pages are what
  the demo shows. The backend's published metadata carries no upper version pins, so it resolves
  against current Django and pydantic. It does import a name removed from its payment provider's
  library at version 8, so the development group holds that library below 8. None of this reaches a
  project that installs this package, because none of it is a dependency of the package.
- A second namespace, for the sake of User Story 5, is defined inside the test suite. There is one
  real backend, and the guarantee under test is that two contributions are independent of each
  other.
- The Account Center, its navigation and its overview are django-mvp's, and this feature adds to
  them through the extension points django-mvp already publishes. Where one is missing, it is
  requested from django-mvp rather than worked around here.
- Views are built on django-mvp's view classes, following the shape of the Account Center's own
  landing page. The restriction to template-rendering views is lifted for this feature and the
  standards document is amended to match. The restrictions that remain are unchanged: no models, no
  migrations, no secret keys, no field a card number could be typed into, no call to a payment
  provider from the server, and no arithmetic that decides what a person is charged.
- Two backends installed at once remains unsupported, and User Story 5 does not change that. The
  guarantee is that adding a namespace is safe, not that two live backends can be reconciled.
