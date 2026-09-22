# Decisions — 003 Offer plans through the provider's own pricing table

Rationale too long to sit inside `spec.md`, plus every ambiguity resolved without asking the
maintainer. The specification stands alone. This file records why it says what it says.

## Why the provider's embed is the default and no plan selection is built

The first reading of this feature built a plan grid from the backend's own records: prices,
billing frequencies, the features recorded against each product, the plan the reader is already on
marked as theirs. The backend supports all of it. The maintainer rejected that shape in favour of
rendering the provider's published pricing table, and the reason is worth keeping.

A project adopting this package has already adopted the backend, and the backend's own
documentation points its readers at the provider's embed. That is the path of least resistance for
every adopter, it requires no markup from anyone, and the provider maintains it. Building a grid
first means building the harder thing, carrying it forever, and maintaining it against a provider
whose catalogue model changes, in service of a requirement nobody has made.

The grid is not refused, it is deferred until somebody asks for it. FR-012 is what makes that
deferral safe: a project that wants its own markup replaces the component or the page template and
keeps everything else. If that override turns out to be what most adopters do, the grid has earned
its place and can be built with evidence behind it.

The cost is stated rather than hidden. An embed is configured in the provider's dashboard from the
provider's catalogue, so it carries the provider's styling and knows nothing about the person
reading it. It cannot mark the plan someone is on, leave out what they cannot buy, or describe what
a plan grants inside the application. A project that needs any of those is a project that overrides
the component.

## Why the script element is not emitted

The provider's dashboard issues a script element and a custom element together, and every example
in its documentation pastes both. This package emits only the second.

Article XIII is the rule, and it is not tidiness. A package that injected a script element would
add a third-party origin to every project that installed it, whether or not that project had
agreed to one. Delivery of a provider's library is a decision projects already make, in whatever
way they already manage their frontend, and it differs between a project using a bundler, one using
an import map and one using a tag. The article anticipated this exact case and says so: a component
wrapping an embed emits the mount point, and the project brings it to life.

The demonstration project loads the library from the provider's own network with a tag, which is
the simplest thing that works and is labelled as a demonstration convenience rather than a
recommendation.

## Why the page may read a publishable key from settings and the component may not

Article XIII currently says a publishable key "is never read from Django settings here" and reaches
a component as an attribute. Applied literally to this feature, the shipped Plans page cannot work:
nobody is passing it attributes, because the whole point of that page is that a project writes no
template for it.

The article's reasoning is about who owns delivery and configuration, not about secrecy. A
publishable key identifies an account and is designed to sit in markup a browser downloads. The
provider prints it in its own copy-paste examples. Nothing is protected by keeping it out of a
settings file, and the real property worth preserving is that the component stays free of hidden
configuration, so it renders anywhere a template author places it.

The split preserves that property exactly. The component takes both values as attributes and reads
no settings, so it is placeable on any page in any project. The Plans page reads the project's
settings and passes them down, which is the same thing it already does for the backend's portal
endpoint. The article's text is narrowed to the component by the work implementing this spec.

The alternative considered was a shipped page that renders nothing until a project subclasses its
view to supply the values. That defeats the goal the page exists for, which is that a working page
arrives without the project building one.

## Why the signed-in person's email address is passed

This is the one decision here that prevents a defect rather than shaping an interface.

The backend maps a provider customer back to an application user by **email address alone**. Its
customer lookup retrieves the customer from the provider, reads the address, and finds the
application user holding it. There is no other identifier in the path. The provider's pricing table
does support a reference value meant for exactly this reconciliation, and the backend reads it
nowhere.

The consequence for a person buying through an embed is concrete. They are signed in, they click a
plan, they land on the provider's checkout, and the address field is empty. They type whichever
address they think of. If it is not the one on their account, one of two things happens. Where the
project has not configured user creation, the backend raises when the purchase arrives and the
subscription attaches to nobody. Where it has, a second application user is created around the
address they typed, and the person who paid still sees nothing on their own subscription page.

Passing the account's address closes it, costs one attribute, and is what the provider's
documentation describes the attribute for. An attribute supplied by a template author wins, because
a project placing the component on a page of its own may have a better answer than the session
does.

## Why the unavailable state is stated rather than shown

The provider's custom element renders as nothing at all when it cannot work, whether because the
script never loaded, the values are missing, or the origin is blocked. A page in that state is not
obviously broken. It looks finished and empty, which is the worst way for a first run to fail,
because there is nothing in it to search for.

So the absence is stated. Where the configuration is missing the page says the plans cannot be
shown and emits no element at all, which is a server-side fact the page already knows. Where the
element was emitted and never came to life, the reader is told the plans could not be loaded, which
is only knowable in the browser and is the same shape as the existing portal control's failure
message.

## What this feature does to the roadmap

R3 and R4 were written as two features: a native plan selection, and an embed offered as the
alternative to it. This feature delivers the embed as the default and defers the selection, so the
two items now describe one piece of work and one deferred idea.

Reconciling the roadmap text is a separate change and does not belong in a specification pull
request. The related intake issue for a checkout handoff is also superseded, because the pricing
table sends a person into the provider's checkout itself, and it is closed with that reason
recorded rather than left open as work nobody will do.

---

## D1 — Design review outcome

One reviewer, three lenses, against `spec.md`, `plan.md`, `research.md`, `tasks.md`, the
constitution and targeted reads of the code the plan names. Verdict **approve**, zero findings at
any severity, so no plan edit and no watch item was carried into any implementation brief.

Two things the review established that are worth keeping:

The two load-bearing claims in `research.md` were spot-checked against the resolved installed
package rather than against documentation. `drf_stripe/stripe_api/customers.py:116-117` in
drf-stripe-subscription 1.2.2 carries the email-only lookup verbatim, and a search for
`client_reference_id` across the whole installed package returns nothing — so the attribute the
provider built for this exact reconciliation really is read nowhere, which is why FR-005 passes the
address instead.

The constitution narrowing was checked for collateral damage and has none. Article XII's "No secret
keys" bullet contains two separate prohibitions: one on an API key, webhook signing secret or
restricted key, and one on a publishable key. Only the second is narrowed. Whoever writes the
replacement text keeps the first package-wide and untouched, because a careless edit to the
surrounding sentence would loosen it.

**ADR:** none — a record of this run's design review, not a standing rule.

---

## D2 — SC-002's script-absence guarantee is held at the template source, not the response

**Decision:** the guarantee behind SC-002 — no script element referencing the provider — is
tested once, statically, against every template this package ships
(`tests.test_app.TestNoProviderScript`, T004). No corresponding assertion is made against the
Plans page's full rendered HTTP response.

**Why:** T004 was written and green before T010 existed. Once T010 adds the demo project's own
`{% block provider_library %}` to `demo/templates/base.html` — loading
`https://js.stripe.com/v3/pricing-table.js`, exactly as Article XIII and the plan's design say a
host project is free to — every page the demo serves inherits that script through the base
template every page extends, the Plans page included. A runtime assertion against the full
response reads that script and fails, not because this package emitted it, but because the demo,
standing in for a host project, correctly did. SC-002's own wording — "every page and placement in
this feature" — means this package's contribution, which T004 already covers exhaustively and
permanently; it does not mean the assembled page a host project's own shell produces around it.

**Revisit if:** a future story needs to assert something about *where* a host project's own script
appears relative to this package's markup — that would be a test of the demo project's own
template, not of `mvp_payments`.

## D3 — US-1 triage: the Plans page's routing assertion was Forge's to update

**Decision:** `tests/test_urls.py`'s parametrized list, which asserts which view each declared page
routes to, now names `PlansPageView` for `drf-stripe-plans`. The Implementer correctly refused to
touch it and reported it as a concern.

**Why:** that test is a pre-existing one the story did not author, and the hard prohibition on
editing such a test exists so a builder cannot make its own work pass by moving the goalposts. The
change here is not that: the test is a registry of which page uses which view, the previous feature
added `SubscriptionPageView` to it the same way, and routing the Plans page through its own view is
what T007's acceptance criterion and the approved plan both require. Updating it is the mechanical
consequence of a design the review approved with no findings, and the party that signs the story
off is the right one to make it.

**Revisit if:** a story ever reports a pre-existing test as blocking where the correct resolution
is not obvious from the approved plan. That one goes back to the maintainer, not through triage.

**ADR:** none — a test registry updated to follow a routing decision ADR 0006 already records.

## D4 — SC-002 is a guarantee about this package's output, not about the demonstration project's page

**Decision:** D2's reading stands. The no-provider-script guarantee is held by the static scan over
every template this package ships, and no assertion is made against the demonstration project's
full rendered response.

**Why:** the specification's own Assumptions section settles it — "The project loads the provider's
pricing table library itself. The demonstration project does it with a tag pointing at the
provider's own network, labelled as a demonstration convenience rather than a recommendation." A
runtime assertion that the demonstration project's page carries no such tag would contradict the
thing the specification says that project is expected to do. SC-002 is about what this package
contributes, and the static scan covers that exhaustively and for every template added after this
feature, which a single page's response assertion never would.

**Revisit if:** this package ever ships a page that does not extend a host project's own shell, in
which case a response-level assertion becomes meaningful again.

**ADR:** none — how one success criterion is tested, recorded against the criterion it belongs to.

## D5 — T012's component-level tests use `cotton_render_string`, not `cotton_render`

**Decision:** the four new `TestPricingTable` cases that need a signed-in `request.user` are
written against `cotton_render_string`, passing an explicit `context={"request": request}`, rather
than against `cotton_render` (the fixture the rest of the class, and the rest of this file, uses).

**Why:** `cotton_render` calls `django_cotton.utils.render_component`, which builds its own
`RequestContext` around the one `HttpRequest` the fixture constructs internally
(`RequestFactory().get("/")`, no `.user` ever attached) and runs the project's configured context
processors against it. `django.template.context_processors.request` always returns `{"request":
<that same request>}`, and a `RequestContext`'s processor-supplied values are looked up ahead of
whatever was in the context dict passed in — so any `request` a caller tries to pass through
`cotton_render`'s `context`/`kwargs` is shadowed by the fixture's own anonymous one before the
template ever sees it. There is no way to give `cotton_render` a request carrying a signed-in user.
`cotton_render_string` builds a plain `Context` (no processors) and sets `context["request"]`
itself from whatever the caller supplied, so the request a test builds — with `.user` attached — is
the one `{{ request.user }}` resolves against in `pricing_table.html`.

**Revisit if:** `mvp`'s `cotton_render` fixture is ever extended to accept a caller-supplied
request; at that point these four tests could move back onto the fixture the rest of the class
uses, for consistency.

**ADR:** none — a test-authoring choice local to this story, not a design decision about the
package.

## D6 — T016's query-count test needs the `db` fixture, for the assertion's own setup rather than for anything the component reads

**Decision:** `test_renders_completely_from_its_attributes_alone_for_an_anonymous_visitor` takes
`db` alongside `django_assert_num_queries`, even though the render under test makes no query
either way.

**Why:** `django_assert_num_queries` opens a `CaptureQueriesContext`, which calls
`connection.ensure_connection()` on entry regardless of how many queries the wrapped code goes on
to make. pytest-django refuses that connection attempt with `RuntimeError: Database access not
allowed` unless the test (or a fixture it depends on) has already enabled db access. Enabling it
does not weaken the assertion — the test still fails if the render makes even one query — it only
lets the zero-query claim be checked at all. This is the reason T016 was red on its first run:
not because the component needed a query, but because the harness that proves it doesn't needed
permission to look.

**Revisit if:** never expected to — this is how `django_assert_num_queries` works everywhere else
it is used against a query-free path.

**ADR:** none — a test-infrastructure fact, not a decision about the package.

## D7 — T018 gives the landing page its two values as literal strings, not through a view

**Decision:** `demo/home.html` writes `table_id="prctbl_not_a_real_table"` and
`publishable_key="pk_test_not_a_real_key"` as literal attribute values on
`<c-drf-stripe.pricing-table>`. `demo/views.py`'s `HomeView` is untouched — still a bare
`MVPTemplateView` with no extra context.

**Why:** this story's claim (T016) is that the component needs nothing but its two attributes —
no view, no context processor, no settings read of its own. A host project's own landing page,
the scenario this story stands in for, would not have a view of this package's to read
`MVP_PAYMENTS` from either; it would just write the identifier and key it already has into its
own markup, the same way it would paste them into any other vendor's embed snippet. Reading them
from `settings.MVP_PAYMENTS` inside `HomeView` would work, but it would demonstrate the wrong
thing: that *this package's* settings can reach an unrelated page, not that the component is
self-sufficient without them.

**Revisit if:** the demo ever needs to vary these values at runtime (a settings-driven demo
toggle, for instance) — at that point reading them from settings in `HomeView` becomes the
simpler choice and this decision should be revisited alongside it.

**ADR:** none — a demonstration-project choice local to this story, not a design decision about
the package.

## D8 — `demo/templates/demo/plans_unconfigured.html` extends the package's own `plans.html`, rather than pointing a view straight at it

**Decision:** `PlansUnconfiguredView.template_name` is `"demo/plans_unconfigured.html"`, a
one-line file under the demo's own `templates/demo/` directory that does nothing but
`{% extends "mvp_payments/drf_stripe/plans.html" %}`. The view does not set
`template_name = "mvp_payments/drf_stripe/plans.html"` directly, though either would render
identically here.

**Why:** T026's own instruction is explicit that "nothing in `mvp_payments/` may know they exist"
about the demo's routes — a property of the package, not of a single view. Extending keeps every
file the demo route touches under `demo/`, the same shape a host project reaching this page would
actually be in: reusing the shipped template through ordinary inheritance, never a package file
edited or pointed at by name from outside `demo/`. A view whose `template_name` is a package path
would work identically today, but would make it one accidental edit away from someone adding
demo-only markup straight into a package file to "customise" this route.

**Revisit if:** never expected to — the file costs one line and keeps the demo self-contained.

**ADR:** none — a demonstration-project choice local to this story.

## D9 — the demo's `no_library` route cannot demonstrate the hidden message being revealed live, because T025's script and the provider's own share one overridable block

**Decision:** `demo/templates/demo/no_library.html` empties `{% block provider_library %}`
exactly as `demo/templates/base.html`'s own comment invites ("A template extending this one can
empty this block to show the mount point with the library never having arrived"), per T026's
literal instruction that the route render "the component on a page whose `provider_library` block
is empty."

**Why this is worth recording:** `demo/templates/base.html` (committed at T010, before this
story, and outside this story's file scope — see the brief's prohibitions) places
`pricing_table.js`'s `<script>` tag *inside* `provider_library`, alongside the provider's own
`pricing-table.js`. Emptying that block for the `no_library` route therefore drops both scripts
together — the route shows the inert `<stripe-pricing-table>` mount point exactly as designed,
but `pricing_table.js` never runs there either, so the hidden could-not-be-loaded message is never
revealed live in a browser on that specific page. The Python test suite has no way to probe this
(there is no JavaScript runtime in these tests), so nothing here is red — this is a demonstration
fidelity gap, not a defect in the package the tests can see. `tests/test_components` and
`tests/test_views` both confirm the message is present and hidden in the component's own markup
(T021), which is the guarantee FR-010 actually makes; the demo route is only asked to make the
*mount point* reachable by clicking (T026's given/when/then), which it does.

**Revisit if:** `demo/templates/base.html` is ever restructured so `pricing_table.js` loads
outside `provider_library` — at that point `no_library.html` could keep emptying the whole block
and the live reveal would work too, or `no_library.html` could override `provider_library` with
partial content (keeping `pricing_table.js`, dropping only the provider's script) instead of
emptying it outright.

**ADR:** none — flagged as a concern in this story's completion report for Forge to triage;
`demo/templates/base.html` is outside this story's scope to edit.

## D10 — `pricing_table.js` moves out of the demo's `provider_library` block, and a test holds it there

**Decision:** `demo/templates/base.html` now loads `pricing_table.js` outside
`{% block provider_library %}`, beside `billing_portal.js`. That block holds the provider's
library and nothing else. `demo/templates/demo/no_library.html` keeps emptying it outright, so the
route drops only the provider's script and our own still runs — the hidden message is revealed
live on the page built to show exactly that.

**Why:** this is D9's triage. D9 recorded the gap accurately and correctly declined to close it,
because `base.html` was outside US-4's file scope. Taking the fix on the second of D9's own
"revisit if" options is the cheaper half: moving one script tag costs nothing, where a partial
block override would have `no_library.html` restating a script tag it does not own and would drift
the moment `base.html` gained another. The block's purpose narrows to the one thing its comment
already claims it is for.

The route existed to demonstrate a state, and without this it demonstrated a different state that
looks identical — a mount point that never comes to life, with no message either way. Nobody
inspecting it would have seen anything wrong.

**How it is held:** `tests/test_demo.py::TestUnavailableStateRoutes` covers both new routes, and
`test_the_no_library_route_drops_the_provider_library_and_keeps_ours` asserts the provider's origin
is absent from that page while `pricing_table.js` is present. Confirmed against the defect: with
the script tag returned to its previous position inside the block, that test fails and the other
three pass.

**ADR:** none — a demonstration-project wiring choice, local to this feature, nothing downstream
inherits it.
