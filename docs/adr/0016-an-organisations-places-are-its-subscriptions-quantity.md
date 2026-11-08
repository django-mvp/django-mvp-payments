# ADR 0016 — An organisation's places are its subscription's quantity

**Status:** accepted, not yet implemented

## Decision

An organisation pays for its members' places through a Stripe subscription of its own, and the
number of places is that subscription's quantity.

- The organisation is a Stripe customer in the same way a person is. Its subscription is recorded
  by the Stripe app as Stripe reports it, quantity included.
- Buying places, and adding or removing them, happens on Stripe's checkout and customer portal, as
  every other change to what someone pays does.
- Which members hold the places is recorded here, because Stripe does not keep it. The
  organisation's owner or admins give and take back places. A member can take a free place with a
  code the organisation handed out. There are never more holders than places.
- Asking whether a person is subscribed answers yes for a member holding a place.
- Organisations are django-organizations' models, presented by django-mvp-accounts. This lives in
  the Stripe app, since a quantity is how Stripe models places, behind an extra that brings in
  django-organizations. A project without it sees nothing of this.
- A discount code is a Stripe promotion code, entered on Stripe's checkout. Joining an
  organisation without a place is an invitation, which is django-mvp-accounts'.

## Why

A quantity on one subscription is how Stripe bills for places. Stripe works out the charge and the
proration when the number changes, and its portal already lets a customer change it, so nothing here
computes a price or builds a billing screen. That keeps the boundary in Article XI: what anyone pays
is decided and changed on the provider's pages.

Stripe has no idea which members hold a place, so that record has to live here. It is the single
exception to local records changing only from the provider. It is safe to make because it cannot
change what anyone pays: the number of places is the quantity, and only Stripe changes that.

## Revisit if

A second provider needs places and models them differently, for example as one subscription per
member. Article XIV then gives that provider its own namespace and its own way of doing it.
