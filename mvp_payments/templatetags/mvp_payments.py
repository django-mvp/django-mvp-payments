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
