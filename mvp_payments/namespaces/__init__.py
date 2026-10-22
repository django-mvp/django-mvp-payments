"""Every namespace this package declares, and which of them are installed.

Every other module reads :func:`available_contributions` rather than asking
``apps.is_installed`` for itself, so the entries, pages and card cannot
disagree about what is installed.
"""

from mvp_payments.contributions import Contribution

from .stripe import stripe_contribution

CONTRIBUTIONS: tuple[Contribution, ...] = (stripe_contribution,)


def available_contributions() -> tuple[Contribution, ...]:
    """Select the declared contributions whose backend is installed.

    Returns:
        The contributions whose backend application is installed.
    """
    return tuple(
        contribution for contribution in CONTRIBUTIONS if contribution.is_available()
    )
