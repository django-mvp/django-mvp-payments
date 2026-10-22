"""Renders each available contribution's card on the Account Center overview, and the plans.

A registered template tag module is an explicit exception to the class
grouping Article X otherwise requires — Django's tag registry is the
extension point here, not a class.
"""

from typing import Any

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import SafeString, mark_safe

from mvp_payments.contributions import Contribution
from mvp_payments.money import Money
from mvp_payments.namespaces import available_contributions
from mvp_payments.namespaces.stripe_plans import PlanChoices
from mvp_payments.namespaces.stripe_records import CurrentSubscription

register = template.Library()


@register.simple_tag
def payment_cards() -> SafeString:
    """Render one card per contribution that is available and reachable.

    Reachability is asked here, before rendering, because a card's
    ``{% url %}`` would raise ``NoReverseMatch`` for a contribution whose
    pages do not reverse, and take the whole overview down with it.

    Returns:
        The cards' markup, empty when no contribution is available.
    """
    # Each piece is already-escaped render_to_string output. str.join drops the
    # SafeString marker, which this restores.
    return mark_safe(  # noqa: S308
        "".join(
            render_to_string(contribution.card_template, _card_context(contribution))
            for contribution in available_contributions()
            if contribution.is_reachable()
        )
    )


def _card_context(contribution: Contribution) -> dict:
    """Build a card's context from the contribution's first page.

    Args:
        contribution: The contribution the card stands for.

    Returns:
        The heading, icon and view name the card template reads.
    """
    first_page = contribution.pages[0]
    return {
        "heading": first_page.label,
        "icon": first_page.icon,
        "page_view_name": contribution.view_name(first_page),
    }


@register.simple_tag(takes_context=True)
def stripe_plans(context: template.Context) -> dict[str, Any]:
    """Gather the plans on offer and how the current reader can buy each.

    Usable in any template whose context carries ``request``, as
    ``{% stripe_plans as plans %}``.

    Args:
        context: The template context, which must hold the request.

    Returns:
        What ``PlanChoices.for_request`` returns for this request.
    """
    return PlanChoices.for_request(context["request"])


@register.filter
def price_money(price: dict[str, Any] | None) -> Money | None:
    """Give a Stripe price's amount in its own currency.

    Args:
        price: A price as the catalogue returns it.

    Returns:
        The amount, or ``None`` when there is no price or it has no amount.
    """
    if not price or price.get("unit_amount") is None:
        return None
    return Money(price["unit_amount"], price.get("currency", ""))


@register.filter
def price_frequency(price: dict[str, Any] | None) -> str:
    """Say how often a Stripe price bills, in words.

    Args:
        price: A price as the catalogue returns it.

    Returns:
        Words such as "every month" or "every 3 months", and an empty string for no price.
    """
    recurring = (price or {}).get("recurring") or {}
    return CurrentSubscription.frequency_words(
        recurring.get("interval", ""), recurring.get("interval_count", 1)
    )


@register.filter
def price_interval(price: dict[str, Any]) -> str:
    """Name a price's billing frequency with the value the interval switch selects.

    Args:
        price: A price as the catalogue returns it.

    Returns:
        The unit and the count, such as ``month_1``.
    """
    return PlanChoices.interval_key(price)
