"""The plans on offer, read from Stripe and kept in the project's cache."""

from __future__ import annotations

import logging
from typing import Any

import stripe
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

from .client import client

logger = logging.getLogger(__name__)

#: Stands for "nothing cached", which a cached ``None`` (Stripe unavailable) is not.
NOT_CACHED = object()


class Catalogue:
    """Reads, filters, orders, caches and clears the prices a project offers.

    A price is on offer when it is active, recurring, licensed, billed per unit with a
    fixed amount, and belongs to an active product. Metered and tiered prices have no
    single amount to show (Article XV).

    Attributes:
        KEY: The cache key the list is kept under.
        UNAVAILABLE_TIMEOUT: Seconds a failed read is remembered, so an outage does not
            hold a worker on every request.
        BILLING_DAYS: How long one interval of each unit bills for, to order prices.
    """

    KEY = "mvp_payments_stripe:catalogue"
    UNAVAILABLE_TIMEOUT = 60
    BILLING_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}

    @classmethod
    def prices(cls) -> list[dict[str, Any]] | None:
        """List the prices on offer, from the cache when it holds them.

        Returns:
            Each price as a plain dictionary with its product expanded, products ordered
            by their cheapest price and a product's prices by billing length. ``None``
            when Stripe cannot be read: no secret key is set, or Stripe failed within
            the last minute.
        """
        cached: list[dict[str, Any]] | None = cache.get(cls.KEY, NOT_CACHED)
        if cached is not NOT_CACHED:
            return cached
        try:
            prices = cls.fetch()
        except ImproperlyConfigured:
            return None
        except stripe.StripeError as error:
            # Not logger.exception: Stripe's message can echo part of the secret key.
            logger.error(  # noqa: TRY400
                "Could not read the Stripe catalogue: %s.", type(error).__name__
            )
            cache.set(cls.KEY, None, cls.UNAVAILABLE_TIMEOUT)
            return None
        cache.set(cls.KEY, prices, cls.timeout())
        return prices

    @classmethod
    def price(cls, price_id: str) -> dict[str, Any] | None:
        """Find one price on offer.

        Args:
            price_id: Stripe's identifier for the price.

        Returns:
            The price, or ``None`` when it is not on offer or the catalogue cannot be read.
        """
        return next((p for p in cls.prices() or [] if p["id"] == price_id), None)

    @classmethod
    def clear(cls) -> None:
        """Forget the cached list, and any remembered failure, so the next read asks Stripe."""
        cache.delete(cls.KEY)

    @classmethod
    def timeout(cls) -> int:
        """Say how many seconds a list read from Stripe is kept.

        Returns:
            ``MVP_PAYMENTS["STRIPE_CATALOGUE_TIMEOUT"]``, an hour when it is not set.
        """
        timeout: int = getattr(settings, "MVP_PAYMENTS", {}).get(
            "STRIPE_CATALOGUE_TIMEOUT", 3600
        )
        return timeout

    @classmethod
    def fetch(cls) -> list[dict[str, Any]]:
        """Read every page of Stripe's active recurring prices and keep those on offer.

        Returns:
            The prices on offer, ordered.

        Raises:
            ImproperlyConfigured: If the secret key is not set.
            stripe.StripeError: If Stripe could not be asked, or refused.
        """
        listed = client().v1.prices.list(
            params={
                "active": True,
                "type": "recurring",
                "expand": ["data.product"],
                "limit": 100,
            }
        )
        prices = [price.to_dict() for price in listed.auto_paging_iter()]
        return cls.order([p for p in prices if cls.is_on_offer(p)])

    @staticmethod
    def is_on_offer(price: dict[str, Any]) -> bool:
        """Say whether a price can be shown with one amount and bought.

        Args:
            price: A price as Stripe returns it, with its product expanded.

        Returns:
            Whether the price is recurring, per unit, licensed, has an amount and has an
            active product.
        """
        product = price.get("product")
        return (
            isinstance(product, dict)
            and product.get("active") is True
            and price.get("type") == "recurring"
            and price.get("billing_scheme") == "per_unit"
            and price.get("unit_amount") is not None
            and (price.get("recurring") or {}).get("usage_type") == "licensed"
        )

    @classmethod
    def order(cls, prices: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Order prices so each product's prices sit together, cheapest product first.

        Args:
            prices: Prices on offer.

        Returns:
            The same prices, ordered by their product's cheapest amount, then the product,
            then how long they bill for.
        """
        cheapest: dict[str, int] = {}
        for price in prices:
            product_id = price["product"]["id"]
            cheapest[product_id] = min(
                cheapest.get(product_id, price["unit_amount"]), price["unit_amount"]
            )
        return sorted(
            prices,
            key=lambda p: (
                cheapest[p["product"]["id"]],
                p["product"]["id"],
                cls.BILLING_DAYS.get(p["recurring"]["interval"], 0)
                * p["recurring"]["interval_count"],
            ),
        )
