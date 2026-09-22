# Adding a namespace

A namespace is one payment backend's corner of this package: the pages it contributes to
django-mvp's Account Center, the navigation entries that lead to them, and its card on the Account
Center's overview. `drf-stripe` is the first one. A second backend gets a namespace beside it
rather than underneath it, and the two share no markup and no data shape.

Nothing here is configured. A namespace contributes when its backend is in the project's
`INSTALLED_APPS`, and contributes nothing when it is not. There is no setting to turn one on.

## What a namespace declares

Everything one namespace contributes is declared as a single `Contribution`, in its own module
under `mvp_payments/namespaces/`:

```python
from django.utils.translation import gettext_lazy as _

from mvp_payments.contributions import Contribution, Page

acme_payments = Contribution(
    backend_app_name="acme_payments",
    namespace="acme",
    pages=(
        Page(
            slug="subscription",
            label=_("Subscription"),
            icon="subscription",
            template_name="mvp_payments/acme/subscription.html",
        ),
    ),
    card_template="mvp_payments/card.html",
    group_label=_("Billing"),
)
```

- **`backend_app_name`** is the backend's full dotted application name — `"drf_stripe"` for a
  package installed at the top level, `"some.vendor.app"` for one installed as a sub-package. It is
  the string Django's application registry matches, and it is never imported: the package declares
  no payment backend as a dependency and must not gain one.
- **`namespace`** is the backend's short name. It prefixes every URL name the contribution
  declares, which is what keeps two namespaces from colliding.
- **`pages`** are the pages this namespace contributes, in the order they should appear in the
  navigation. A `Page`'s `slug` names it within the namespace, its `label` is what a person reads
  and must be translatable, its `icon` is a name from the project's icon set, and its
  `template_name` is the template the page renders.
- **`Page.in_navigation`** decides whether that page gets an entry in the menu. It defaults to
  `True`. Set it `False` for a page that is reached from somewhere else — the shipped namespace's
  plans page is reached from a control on its subscription page — and the page is still routed,
  still reverses and still renders. Reachable and navigable are different questions, and a menu
  only answers the second.
- **`card_template`** renders this namespace's card on the Account Center's overview.
- **`group_label`** heads the section this namespace's pages sit under in the Account Center's
  navigation, and must be translatable. Label it for what a reader will find there, not for the
  library behind it — django-accounts-center heads its own section of the same menu
  "Email & Authentication", and nobody reading their own subscription page has a use for the name
  of a Python package.

The shipped namespace follows exactly that shape: `drf_stripe`, in
`mvp_payments/namespaces/drf_stripe.py`, declaring a subscription page and a plans page against
the `drf_stripe` application name, under a `Billing` group. Only the subscription page is in the
navigation. One entry rather than several is a deliberate choice about what an adopter's readers
see: the plans page is reached from the subscription page, because somebody choosing a plan is
already looking at the one they are on.

Register a new contribution by adding it to `CONTRIBUTIONS` in
`mvp_payments/namespaces/__init__.py`. Everything else follows from that: the URL configuration
mounts its pages, `ready()` adds its navigation group, and the overview renders its card.

## The two questions a contribution answers

`Contribution.is_available()` asks the application registry whether the backend is installed, and
nothing else. The application's `ready()` and the URL configuration both call it, and neither may
reverse a URL at the point it runs.

`Contribution.is_reachable()` asks a second question on top of that one: whether the namespace's
pages actually reverse, which answers whether the project has mounted this package's URLs. Only
something rendering a page may ask, because reversing needs the URL configuration already loaded.
The card uses it: a card whose link cannot resolve would take the whole overview down with it.
Navigation entries do not need it. django-flex-menus already hides an entry whose URL will not
reverse, and a group left with no visible children goes with them.

`available_contributions()` in `mvp_payments/namespaces` returns the installed ones. Read it rather
than asking the application registry yourself, so that the entries, the pages and the card cannot
disagree about what is installed.

## Pages

Every contributed page is served by `PaymentPageView`, which takes its template and heading from
the `Page` it was built for. It requires a signed-in person and makes no finer access decision than
that: who among the signed-in people may see what is the host project's to enforce, because this
package holds no entitlement information.

A page template extends `mvp/account/base.html` and fills its content block, so the page renders
inside the Account Center with the navigation beside it.

A view is handed its contribution as well as its own page, so a page can address a sibling without
a copy of the URL-name format anywhere: `self.get_contribution().page_url("plans")` returns that
page's address. That is how the shipped subscription page links to a plans page that is no longer
in the menu.

## What a namespace may not do

The boundaries in [CONSTITUTION.md](../CONSTITUTION.md) apply to every namespace: no models, no
migrations, no forms or admin or serializers, no secret keys, no field a card number could be typed
into, no call to a payment provider from the server, and no arithmetic that decides what a person
is charged. A page may read the records an installed backend keeps, through Django's application
registry, and render them.
