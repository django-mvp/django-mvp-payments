# ADR 0005 — The provider's portal is reached by posting to the backend, from a static file

**Status:** accepted

## Decision

`<c-drf-stripe.portal-link>` renders a control carrying the backend's endpoint and a CSRF token as
data. `billing_portal.js`, shipped as a static file with no build step, binds that control, posts,
follows the address the backend answers with, and reveals the control's own hidden message when it
cannot. The host project loads that file the way it loads its other static assets, and tells the
page where it mounted the backend's endpoint.

## Why

The backend's portal endpoint answers a POST with JSON and carries no route name, so it can be
neither linked to directly nor reversed. Two simpler routes were available and both fail.

A view of ours that called the endpoint and redirected would make this package call a backend
endpoint on a reader's behalf. The constitution reserves that for the backend, which is the package
whose job it is.

A plain form posting at the endpoint would land the reader on a page of raw JSON, because the
endpoint answers with an address rather than a redirect.

The endpoint's location is not ours to know. Mounting the backend's URLs is the project's decision
and it may mount them anywhere, so a component that assumed a path would work in the demo and
nowhere else.

The script never writes the backend's response into the page. Its failure message is static,
translated text the template rendered, so it stays translatable and nothing that came back over the
wire reaches the document.

## Revisit if

A backend exposes a portal route that can be reversed and answers with a redirect, at which point
an ordinary link replaces all of this for that backend.
