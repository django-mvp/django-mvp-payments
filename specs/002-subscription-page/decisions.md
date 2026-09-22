# Decisions — 002 Show a person the subscription they are on

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without asking the
maintainer. The specification stands alone. This file records why it says what it says.

## Why "currently subscribed" is the backend's definition and not ours

The first reading of this feature tried to enumerate the states a subscription can be in and give
each one its own treatment: on trial, past due, incomplete, scheduled to stop at the end of the
period, ended. The maintainer rejected that shape, and the reason generalises past this page. We
cannot anticipate what any given application needs, so a page built to cover every scenario is a
page built on guesses about applications that do not exist.

What we can do is take facts the chosen backend actually determines. It already draws the line
this page needs: it answers questions about a person's access from a fixed set of statuses, which
are active, trialing and past due, and excludes cancelled, ended and unpaid. That line is applied
everywhere else the backend is asked about a person, so a page that drew its own would disagree
with the rest of the application that installed it. A person locked out of a feature would be
reading a page telling them their subscription is fine.

This also disposes of the multiple-subscription question without a rule of our own. The backend
returns what it returns. The page renders each one rather than choosing between them, which is
both simpler than picking and the only answer that cannot silently hide something.

## Why there is no total

A subscription can cover several priced items, and the obvious thing to put at the bottom of a
list of amounts is their sum. It would be wrong. The backend records a unit amount and a quantity
per item and holds nothing about tax, discounts, coupons or proration, so any sum computed here
is a number that looks authoritative and is not what the person will be charged.

`CONSTITUTION.md` Article XII forbids it independently, and the two reasons are the same reason:
a figure this package worked out is a figure the backend did not stand behind. Showing each item
as the backend recorded it says less and is true.

## Why the portal is reached through the backend

The maintainer's floor for this page is that it tells a person their subscription is managed by
the provider and takes them there. Article XII forbids this package from calling a provider, so
the question is where the address comes from.

The backend already answers it. It exposes an endpoint that mints a portal session for the
signed-in person and replies with its address, which means the provider call is made by the
package whose job that is. The page asks the backend and follows the answer.

That endpoint's location is not ours to know. Mounting the backend's URLs is the project's
decision and it may mount them anywhere, so the page is told where to ask rather than assuming a
path. A component that hard-coded one would work in the demo and nowhere else.

## Why features come from the plan rather than from the person

The backend can answer both questions: the features recorded against a product, and every feature
a person has access to across all their current subscriptions. The second is the more useful
answer to "what can I do in this app", and it is the wrong one to print beside a plan's name.

A person holding two subscriptions would read the combined list under the first plan and conclude
that plan grants all of it. Cancelling it would then take away things they thought they were
keeping. The per-plan list is narrower and cannot be misread.

## Why the page ships components and context rather than only markup

The maintainer named this as the deliverable rather than a nicety: no default page can anticipate
what a given application needs, so the measure of a good one is how cheaply it is replaced.

Two things make that cheap, and they are different. A project that wants different wording or a
different arrangement overrides the template, and needs every value the shipped page had to be
already in the context under a name it can use. Otherwise overriding the template means also
writing a view, and the package has given away nothing. A project that wants a piece of this page
somewhere else entirely needs that piece to be a component that renders from its attributes, with
no dependence on this page's view having run.

Both are stated as requirements rather than left to the implementation, because both are
invisible from the rendered page. A page can look right while being impossible to override.

## Why an unrecognised status is shown rather than handled

The backend stores the status as the provider sent it, and providers add statuses over time. The
set in the backend's own code is already a snapshot of one moment. A page that renders only
the statuses known when it was written goes blank, or worse renders nothing where a state should
be, the first time a new one arrives, in a deployment nobody is watching.

Showing the recorded value is not a fallback. It is the honest rendering of a value this package
does not own.

## Where this leaves the roadmap

The roadmap item this feature comes from, R2, is one of five under the first release gate, and R5,
reaching the provider's billing management, is now substantially delivered here. The
maintainer's floor for this page included the portal handoff, so splitting it back out would mean
shipping a page that deliberately withholds its most useful link for several weeks.

R5 is rewritten to whatever remains of it, or retired, rather than left in the roadmap describing
work this feature has done. That is a roadmap change and it is recorded here because this feature
is what caused it.

## D1 — "Current" is read from the backend's own property, not from a status filter of ours

The specification says the page takes the backend's definition of current (FR-001). The backend
offers two ways to honour that. Its `StripeUser` exposes `current_subscription_items`, which
filters on the status set it uses everywhere else; or a caller can filter subscriptions on that
same set directly, which means naming the statuses.

The page reads the property and groups its rows by subscription. The status set then lives in
exactly one place — the backend's — and the day it changes there, this page changes with it. The
alternative puts a copy of that list in a package that has no way to know it has gone stale, which
is precisely the disagreement between page and application the specification's first clarification
was written to prevent.

The cost is that a current subscription with no priced items would not appear. The backend records
a subscription's items from the provider's own line items, so a subscription without them is not a
state the provider produces.

**ADR:** to be recorded at convergence.

## D2 — An amount's minor-unit exponent is a table in this package

Article XVI forbids assuming two decimal places, and the backend records only an integer of minor
units and a three-letter code. Something has to hold the exponent.

`babel` holds it, along with a localised currency pattern, and was rejected. It is a runtime
dependency with a data bundle attached, for a table of twenty-three currency codes this package can
state in a dozen lines, and Article VII asks for a justification that does not exist here. The
consequence accepted with it is that the currency renders as its code beside a localised number
rather than as a symbol inside the locale's own pattern.

Converting minor units for display is not the figure FR-007 forbids. That requirement is about
producing a number the backend did not record — a total, a proration, a conversion between
currencies. Rendering 2000 minor units of a two-decimal currency as 20.00 is the same value written
the way the currency is written, and rendering it any other way would be wrong.

**ADR:** to be recorded at convergence.

## D3 — The portal is reached by posting to the backend, from a static file

The backend's portal endpoint answers a POST, returns the address in JSON, and carries no route
name, so it can be neither linked to directly nor reversed. Three routes were available.

A server-side view of ours that called the endpoint and redirected was rejected: it would make this
package call a backend endpoint on a reader's behalf, and Article XII reserves that for the
backend.

A form posting straight at the endpoint was rejected because the endpoint answers with JSON rather
than a redirect, so the reader would land on a page of JSON.

What ships is a control carrying the endpoint and a CSRF token as data, and a small static file
that posts, follows the address that comes back, and reveals a message when it cannot. Article XIII
already provides for exactly this: logic a component needs of its own arrives as a small static
file with no build step, and the project includes it the way it includes everything else.

**ADR:** to be recorded at convergence.

## D4 — `Page` learns which view renders it

Until now every contributed page was the same view with a different template, which was right while
the pages were empty. This one needs context the generic view cannot supply.

`Page` gains a `view` field defaulting to the existing one, and the routes are built from it. The
alternative — a second URL configuration for the pages that need their own view — would put one
namespace's routes in two places and break the property the previous feature was built around, that
a contribution declares everything it contributes and one condition decides all of it.

**ADR:** to be recorded at convergence.

## D5 — Withholding the portal control is a safety property, not only a courtesy

The specification's clarification for FR-008 reasons that a person with no customer record has
"nothing on the other side of the link". The design review checked that against the backend as it
is actually installed, and it is not what happens. The portal endpoint calls
`get_or_create_stripe_user`, which creates the missing row and then creates a **new customer at the
provider** before minting a session for it. A person who had never subscribed would, by clicking,
acquire a customer record at Stripe.

The requirement is unchanged and no behaviour moves: the page already withholds the control from
anyone with nothing current, which covers the narrower case. What changes is why. The reason is
recorded here, and in `research.md`, so that a later reader tempted to "fix" the empty state by
offering the link anyway can see what it would cost. The specification's own sentence is wrong in
its reasoning rather than in what it requires, so it is left alone and the correction lives here.

**ADR:** to be recorded at convergence.

## D6 — Design review outcome

One reviewer, three lenses, one round. Verdict `approve`, no critical or high findings, so no
re-plan.

Three findings, each recorded rather than escalated:

- **DR-001** (medium, verified) — the false premise behind FR-008, above. Recorded as D5; no task
  changed.
- **DR-002** (medium, likely) — the reader's queryset was described as reaching only the product,
  while the grouping reads `item.subscription` from every row, which is a query per item. `plan.md`
  and T009 now name `select_related("subscription", "price__product")`, and T007 holds it with a
  query-count assertion rather than leaving it to inspection.
- **DR-003** (low, likely) — `Price.nickname` and `Product.name` are both nullable, so a plan can
  in principle have no name at all, where the parallel case for a feature has a stated fallback.
  Carried as a watch item on US-1 rather than invented into the page: the provider requires a
  product name at creation, so the gap is a schema possibility and not a path a reader reaches.

Two editorial corrections were made in the same pass: a miscount of the currency table, and wording
that read as though stories shared one working tree.

**ADR:** none — a record of this run's design review, not a standing rule.
