# ADR 0005 — The provider's portal is reached by posting to the backend, from a static file

**Status:** accepted

## Decision

`<c-stripe.portal-link>` renders a control carrying the endpoint of the Stripe app's billing-portal
view and a CSRF token as data. `billing_portal.js`, shipped as a static file with no build step,
binds that control, posts, follows the address the view answers with, and reveals the control's own
hidden message when it cannot. The host project loads that file the way it loads its other static
assets. The page finds the view by reversing its URL name, so it is told nothing about where the
project mounted the package's URLs.

## Why

Opening a portal session asks Stripe to create something, so it is a POST and not a link. A form
posting at the view would land the reader on a page of raw JSON, because the view answers with an
address rather than a redirect, and an address is what lets the script show a failure in place when
Stripe cannot be reached instead of leaving the reader on an error page.

Where the view is mounted is not ours to know. The project mounts this package's URLs anywhere, so
a component that assumed a path would work in the demo and nowhere else. The page reverses the name
and hands the component the result.

The script never writes the view's response into the page. Its failure message is static,
translated text the template rendered, so it stays translatable and nothing that came back over the
wire reaches the document.

## Revisit if

Stripe offers a portal address that can be linked to directly, at which point an ordinary link
replaces all of this.
