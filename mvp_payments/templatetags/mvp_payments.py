"""Renders each available contribution's card on the Account Center overview.

A registered template tag module is an explicit exception to the class
grouping Article X otherwise requires — Django's tag registry is the
extension point here, not a class.
"""

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import SafeString, mark_safe

from mvp_payments.contributions import Contribution
from mvp_payments.namespaces import available_contributions

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


# SKETCH (FS-005): what the plans components read. The build decides where these live.


@register.simple_tag(takes_context=True)
def stripe_plans(context) -> dict:
    """The plans on offer and how the current reader can buy each, for any template."""
    from mvp_payments.namespaces.stripe_plans import PlanChoices

    return PlanChoices.for_request(context["request"])


@register.filter
def price_money(price: dict):
    """A Stripe price's amount, as Money in its own currency."""
    from mvp_payments.money import Money

    if not price or price.get("unit_amount") is None:
        return None
    return Money(price["unit_amount"], price.get("currency", ""))


@register.filter
def price_frequency(price: dict) -> str:
    """How often a Stripe price bills, in words: every month, every 3 months."""
    from mvp_payments.namespaces.stripe_records import CurrentSubscription

    recurring = (price or {}).get("recurring") or {}
    return CurrentSubscription(
        status="",
        name="",
        amount=None,
        interval=recurring.get("interval", ""),
        interval_count=recurring.get("interval_count", 1),
        period_start=None,
        period_end=None,
    ).frequency_display


@register.filter
def price_interval(price: dict) -> str:
    """One key per billing frequency, the value the interval switch selects."""
    from mvp_payments.namespaces.stripe_plans import PlanChoices

    return PlanChoices.interval_key(price)
