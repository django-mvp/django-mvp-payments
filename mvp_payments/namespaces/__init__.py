"""Every namespace this package declares, and which of them are installed.

Every other module reads :func:`available_contributions` rather than asking
``apps.is_installed`` for itself, so the entries, pages and card cannot
disagree about what is installed.
"""

from mvp_payments.contributions import Contribution

from .drf_stripe import drf_stripe

CONTRIBUTIONS: tuple[Contribution, ...] = (drf_stripe,)


def available_contributions() -> tuple[Contribution, ...]:
    """The declared contributions whose backend is installed."""
    return tuple(
        contribution for contribution in CONTRIBUTIONS if contribution.is_available()
    )
