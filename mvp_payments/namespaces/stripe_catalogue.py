"""SKETCH ONLY: a stand-in for the Stripe app's cached catalogue.

The build replaces this with the Stripe app reading Stripe and caching the result
(FS-005, FR-014). Until then it returns Stripe-shaped price dictionaries, with their
products expanded, so the plans components render from the shape they will receive.
A ``?sketch=`` query parameter picks which catalogue is shown, so every state the page
must answer for can be opened directly.
"""

from __future__ import annotations

from typing import Any

FEATURES = {
    "basic": ["One project", "Monthly usage report", "Email support"],
    "pro": [
        "Up to ten projects",
        "Weekly usage reports",
        "Priority email support",
        "Export to CSV and Excel",
    ],
    "team": [
        "Unlimited projects",
        "Up to 25 team members, each with their own sign-in",
        "Daily usage reports",
        "Support by email and phone",
        "Single sign-on",
    ],
}


def product(key: str, name: str, description: str | None) -> dict[str, Any]:
    """A Stripe product, as the API returns it expanded on a price."""
    return {
        "id": f"prod_demo_{key}",
        "object": "product",
        "active": True,
        "name": name,
        "description": description,
        "marketing_features": [{"name": f} for f in FEATURES.get(key, [])],
    }


def price(
    price_id: str,
    prod: dict[str, Any],
    unit_amount: int,
    currency: str = "usd",
    interval: str = "month",
    interval_count: int = 1,
) -> dict[str, Any]:
    """A Stripe recurring price, with its product expanded."""
    return {
        "id": price_id,
        "object": "price",
        "active": True,
        "type": "recurring",
        "billing_scheme": "per_unit",
        "unit_amount": unit_amount,
        "currency": currency,
        "recurring": {"interval": interval, "interval_count": interval_count},
        "product": prod,
    }


def standard() -> list[dict[str, Any]]:
    """Three products, each with a monthly and a yearly price."""
    basic = product("basic", "Basic", "For one person getting started.")
    pro = product("pro", "Pro", "For people who use it every day.")
    team = product(
        "team",
        "Team",
        "For a group working on the same projects, with one bill for everyone.",
    )
    return [
        price("price_demo_regular", basic, 2000),
        price("price_demo_basic_year", basic, 20000, interval="year"),
        price("price_demo_pro_month", pro, 5000),
        price("price_demo_pro_year", pro, 50000, interval="year"),
        price("price_demo_team_month", team, 12000),
        price("price_demo_team_year", team, 120000, interval="year"),
    ]


def single() -> list[dict[str, Any]]:
    """One product with one price, so there is nothing to switch between."""
    basic = product("basic", "Basic", "For one person getting started.")
    return [price("price_demo_regular", basic, 2000)]


def many() -> list[dict[str, Any]]:
    """Six products, monthly only, one with a long name and no description."""
    names = [
        ("starter", "Starter", "Try it out on a single small project."),
        ("basic", "Basic", "For one person getting started."),
        ("plus", "Plus", "A little more room than Basic."),
        ("pro", "Pro", "For people who use it every day."),
        ("team", "Team", "For a group working on the same projects."),
        ("institution", "Institution-wide research data licence", None),
    ]
    return [
        price(f"price_demo_{key}_month", product(key, name, desc), 1000 * (i + 1) ** 2)
        for i, (key, name, desc) in enumerate(names)
    ]


def currencies() -> list[dict[str, Any]]:
    """Prices in zero-decimal and three-decimal currencies, and a quarterly price."""
    premium = product("premium", "Premium", "Billed in yen.")
    gulf = product("gulf", "Gulf", None)
    gulf["marketing_features"] = []
    quarterly = product("quarterly", "Quarterly", "Billed every three months.")
    return [
        price("price_demo_regular_premium", premium, 500000, currency="jpy"),
        price("price_demo_gulf_month", gulf, 12500, currency="kwd"),
        price(
            "price_demo_quarterly",
            quarterly,
            5400,
            currency="eur",
            interval="month",
            interval_count=3,
        ),
    ]


CATALOGUES = {
    "": standard,
    "single": single,
    "many": many,
    "currencies": currencies,
    "empty": list,
}


class SketchCatalogue:
    """What the plans page reads in place of the Stripe app's catalogue, for the sketch."""

    @staticmethod
    def prices(variant: str) -> list[dict[str, Any]] | None:
        """The prices on offer, or ``None`` when the catalogue cannot be read.

        Products are ordered by their cheapest price, and a product's prices by how long
        they bill for, so ``{% regroup %}`` on the product keeps them together.
        """
        if variant == "unavailable":
            return None
        catalogue = CATALOGUES.get(variant, standard)()
        cheapest: dict[str, int] = {}
        for p in catalogue:
            pid = p["product"]["id"]
            cheapest[pid] = min(cheapest.get(pid, p["unit_amount"]), p["unit_amount"])
        days = {"day": 1, "week": 7, "month": 30, "year": 365}
        return sorted(
            catalogue,
            key=lambda p: (
                cheapest[p["product"]["id"]],
                p["product"]["id"],
                days[p["recurring"]["interval"]] * p["recurring"]["interval_count"],
            ),
        )
