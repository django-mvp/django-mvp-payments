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
