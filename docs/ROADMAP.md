# Roadmap — django-mvp-payments

**Date:** 2026-09-21

This document was designed against [GOALS.md](../GOALS.md). See also [CONTEXT.md](../CONTEXT.md)
for domain terminology and [CONSTITUTION.md](../CONSTITUTION.md) for project standards.

## Versioning

Releases are gated on goal importance rather than on a count of features.

| Version | Gate |
|---|---|
| `0.0.x` | Building toward the Essential goals. Pre-viable, expect churn, nothing published. |
| `0.1.0` | All Essential goals delivered. The minimum usable release, and the first publish. |
| `0.1.x` → `0.x` | Advancing the Expected goals, at whatever granularity the work takes. Patches are fixes. |
| `1.0.0` | All Expected goals delivered. The complete, dependable release. |
| `1.x` | Stable line: non-breaking fixes and additive features only. |
| `2.0` | Next major, where breaking changes go. |

A goal is not one minor version. Some take several, and one minor can move two. Once `1.0` ships,
a breaking change never goes out as `1.x`. It waits for the next major.

*Aspirational goals may be developed against v2 or v1 as required. There are none today.*

## Essential goals: v0.1.0

Everything needed for a project to install this beside a backend and have working pages.

### R1 — Pages that arrive on their own

*delivered in [#6](https://github.com/django-mvp/django-mvp-payments/issues/6) · advances G1, G3*

A project that installs this package alongside a payment backend gets that backend's pages in the
Account Center without writing a view, a template or a menu entry. What is in the installed-apps
list decides what exists: install a backend and its pages appear, leave it out and nothing from it
does. This comes first because every later item is a page that arrives through it, and because the
arrival mechanism is what makes the package worth installing at all rather than copying a template
out of it.

It is also where the separation between backends becomes real rather than intended. A namespace
contributes its own entries and its own card, and nothing it contributes can reach another
namespace's pages.

**Deliverables:**

- Installing a backend alongside this package puts that backend's pages in the Account Center,
  with no code in the project beyond mounting this package's URLs once.
- A backend that is not installed contributes nothing, and costs the project none of its
  dependencies.
- A page that is not reachable does not appear as a broken entry.
- Adding a second namespace leaves the first one's pages untouched.

Serves G1 and G3. Does not cover what any individual page shows.

### R2 — A person can see where they stand

*delivered in [#16](https://github.com/django-mvp/django-mvp-payments/issues/16) · advances G1, G4*

The first destination those entries lead to: what this person is subscribed to, what it costs,
which billing period they are in, and what happens next. This is the page an adopter would
otherwise build first and the one they would get wrong most often, because the interesting part is
not the healthy case. A subscription can be on trial, past due, incomplete, scheduled to stop at
the end of the period, or already over, and each of those means something different to the person
reading it.

It comes second because R1 gives it somewhere to appear, and because the arrival mechanism is not
demonstrably working until something real is on the other side of it.

**Deliverables:**

- A signed-in person can see their current subscription, its price, its billing frequency and its
  period.
- Every state the backend can report is shown and distinguishable, not just an active one.
- A person with no subscription sees that plainly, rather than an empty page.
- Amounts are correct in whichever currency the project sells in.

Serves G1 and G4. Does not cover changing the subscription, which belongs to the provider.

### R3 — A person can choose a plan and start paying

*feature · advances G1, G2*

Plans a person can pick from, and a way to pay for one, in the two positions a project needs them:
the Plans page in the Account Center, and any page of the project's own, a public landing page
being the obvious one.

The provider already publishes a pricing table built for exactly this, configured in its own
dashboard and maintained by the people whose catalogue it draws on. That is what this item places.
An adopter gets working plans from one tag and some configuration, which is the shortest route
there is from installing the package to taking money, and it is the route the backend's own
documentation already points its readers at.

The trade is worth stating where an adopter will read it. An embed carries the provider's styling
and knows nothing about the person looking at it, so it cannot mark the plan someone is already on,
leave out what they cannot buy, or describe what a plan grants inside the application. A project
that needs any of that replaces the component with markup of its own and keeps everything else the
package gives it. Building a plan selection from the backend's records is a much bigger thing to
own, and it waits for an adopter to ask for it rather than being built on the guess that one will.

**Deliverables:**

- A project supplies a published pricing table and gets a working plan-choosing page, having
  written no view and no template.
- The same thing can be placed on any page the project owns, including one with no signed-in
  person.
- Choosing a plan takes a person into the provider's own checkout, and what they buy is attached
  to their account.
- A project that wants its own markup replaces it without writing a view.
- None of it brings in a dependency or an external origin the project did not already have.

Serves G1 and G2. Does not cover taking payment, which happens on the provider's pages, and does
not cover building an alternative to the provider's embed.

### R5 — The handoff to the provider survives a page left open

*resolve · advances G4*

Reaching the provider's own portal to change a payment method, read an invoice or cancel is a
control on the subscription page, and it works. What is not built is the case where a person opens
that page, goes away, and comes back to click, which is the ordinary way a page like this gets
used. The control carries a token minted when the page rendered, so a session that has moved on
since means the handoff fails, and what the reader is told is to try again later when reloading is
what would actually help.

**Deliverables:**

- A person who left the page open and came back still reaches the provider.
- Where that is not possible, what they are told is something they can act on.

Serves G4. It is small, and it is the last thing between a subscriber and everything they can
actually do. G4 as a whole still gates v1.0.0. Does not cover reproducing anything the provider's
own pages already do.

## Expected goals: v1.0.0

The rest of the coverage of what the installed backend can do.

### R6 — Coming back from checkout says something useful

*resolve · advances G4*

A person returning from the provider's checkout lands back in the application, and what they see
should reflect what they just did. The catch is that the provider confirms the payment to the
backend separately from sending the person home, so the page can be reached before the backend
knows anything has changed. Showing "no subscription" to someone who has just paid is the failure
worth designing against.

**Deliverables:**

- A person returning from a completed checkout is told it worked.
- A return that arrives before the backend has caught up does not read as a failure.
- A cancelled or abandoned checkout returns somewhere sensible.

Serves G4. Does not cover confirming the payment, which is the backend's.
