# Planning notes — 005 Show the plans we offer and let only signed-in users buy one

Suggestions for how this is built, from the maintainer. Research answers each one by name. Add
to this file at any time before the build starts.

## From the intake issue (#61)

Read the active prices and their products from Stripe and keep them in Django's cache, rather than copying them into models. The webhook endpoint already in the package clears the cache when a product or price changes (`product.*`, `price.*` events). The cache also expires on a timer, as a backstop for a missed webhook.

Start Stripe Checkout from a view of our own that requires sign-in, and create the session on the server with the user's existing Stripe customer and the signed checkout reference. That way Stripe never sees a purchase that isn't tied to an account. Checkout itself stays on Stripe's hosted page.

Plans and prices are managed in Stripe's product catalogue. Product metadata or marketing features can carry a short description or feature list for each plan card.

Product and Price models are not needed for this. They would be worth adding only when a project needs reports or queries by plan, or a catalogue too large to fetch, and they would be kept in step through the same webhooks.

The plan cards are new design, so they should be sketched and agreed on the running page before they are built.

## From the specification discussion, 2026-10-22

"I assume we will be building the page from a json payload from Stripe?" Agreed: the Stripe app lists the active recurring prices with their products expanded in the same call, keeps the result in the cache as plain dictionaries, and the page renders from it. A project overriding a part reads Stripe's own documented fields (`unit_amount`, `currency`, `recurring.interval`, the product's `name`, `description` and `marketing_features`), not a format of this package's.

Alpine.js templating was considered as the way for host projects to customise the plans: an outer template taking the whole data object, with partial templates declared inside `<template>` tags and filled from the part of the data each needs. Agreed instead: the same shape built from Cotton components rendered on the server. An outer component takes the whole catalogue, and inner components take one price, its amount or its product's features. A project replaces one part for the whole site by shipping a template at the same path, or on one page through a slot. The plans page is public, so it has to arrive as HTML for search engines and for readers without JavaScript, and Article XV's money formatting and its rendered-output tests stay on the server. Alpine is still the right tool for switching between monthly and yearly prices on cards the server has already drawn, and django-mvp's base template already loads it.
