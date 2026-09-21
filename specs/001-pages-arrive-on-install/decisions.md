# Decisions — 001 Pages that arrive on install

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without asking the
maintainer. The specification stands alone; this file records why it says what it says.

## Why the pages arrive empty

The alternative was to ship the arrival mechanism proved by a single page and let each later
feature add its own route and navigation entry alongside its content. That reading was put to the
maintainer at intake and not taken.

Routing a page and filling it are different kinds of work, and splitting them per feature would
mean every later feature re-deciding where its page lives, what its address is and where its entry
sits — five chances to answer the same question differently. Deciding the shape of the page set
once, here, is what makes the later features additive. The cost is a period during which three
pages render a heading and nothing else, and the release gate for this stage already states that
it is pre-viable with nothing published.

No placeholder copy goes on those pages. Text apologising for an empty page is text written to be
deleted, and it would be the only thing on the page that no later feature owns.

## Why the demo installs the real backend

The first reading put to the maintainer was that the backend could not be installed here at all —
that its pins would reach this repository's own environment, so a stand-in application carrying
the same label would have to simulate it. He rejected that, and the rejection was right on the
facts.

The backend's published metadata declares `Django>=3.0`, `pydantic>=1.8` and `stripe>=2.63` with
no upper bound on any of them. The pinning described in the working notes was never true of the
published distribution. It resolves cleanly here against current Django and pydantic 2.

One real incompatibility survives. The backend imports a name from its payment provider's library
that was removed at version 8, so anything importing that module raises on a current release. The
development group therefore holds that library below 8. This is a development dependency of this
repository and nothing else: the package declares no backend, so no project installing it inherits
the constraint, which is the entire point of the dependency rule.

A stand-in would also have been worse on the merits. The claim under test is that installing a
backend makes its pages appear, and a stand-in tests that installing *something named like* a
backend makes pages appear.

## Why a second namespace exists only in the test suite

User Story 5 is the one guarantee that cannot be demonstrated with the backends that exist, because
there is exactly one. The claim is about independence between two contributions, and independence
needs two contributions and nothing else — not two real payment libraries. A second namespace
defined in the test suite, contributing through the same mechanism, answers it completely.

This does not reopen the question above. The demo installs a real backend because the demo is what
a person looks at. The test suite defines a second namespace because the property under test is
structural.

## Why entries sit directly in the navigation

A parent entry grouping a backend's pages would need a label, and the only accurate label is the
name of a Python library. Nobody reading their own subscription page has any use for that word, and
inventing a friendlier one would put a name on the navigation that appears nowhere else.

Grouping only pays when two backends are installed at once, and that is already unsupported, for a
reason that has nothing to do with navigation: with two live backends, whose subscription a person
is looking at stops being answerable, and nothing in this package arbitrates it.

## Why views were allowed to grow beyond rendering a template

The project's standards document restricted every view here to one that hands a template to the
renderer, on the reasoning that anything more would make the package a participant in the
application rather than a supplier of markup. The maintainer lifted that restriction at intake.

The consequence is larger than the sentence it changes, and it is recorded here because later
features inherit it. A page may now read the backend's records on the server and render them,
rather than every value arriving in the browser from the backend's HTTP endpoints. That makes the
components server-rendered markup with a context, and it is why the domain glossary's description
of how components reach a backend changes with this feature.

What did not change: no models, no migrations, no secret keys, no field a card number could be
typed into, no call to a payment provider from the server, and no arithmetic that decides what a
person is charged. Those are the package's identity rather than a restriction on how a page is
built. The no-dependency rule survives too, because a page reaches a backend's records through the
application registry rather than by importing the backend.

## Why the working notes are deleted rather than corrected

The founding notes carry a section arguing that the package ships no Python beyond an application
configuration, which the standards document and the README already contradicted before this
feature and which this feature contradicts outright. The maintainer's instruction at intake was
that the file is obsolete. Correcting one section of a document whose premise has moved leaves a
reader trusting the rest of it. The prior-art survey it also carries is preserved where it is
already stated — in the README's scope section and in the standards document's own articles.
