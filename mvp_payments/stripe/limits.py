"""How often one person may make the app ask Stripe for something."""

from __future__ import annotations

import time
from dataclasses import dataclass

from django.core.cache import cache


@dataclass(frozen=True)
class RateLimit:
    """A count of one person's requests in fixed windows, kept in the project's cache.

    A view that creates something at Stripe for whoever posts to it checks one of these first.
    CSRF stops another site from posting, but not the person themselves, and one account
    posting in a loop spends the Stripe account's rate limit for everyone. The count is per
    process with a local-memory cache and shared with any other.

    Attributes:
        name: Names what is counted, so two limits never share a count.
        limit: How many requests a person may make in one window.
        seconds: How long a window lasts.
    """

    name: str
    limit: int
    seconds: int

    def allows(self, user) -> bool:
        """Count this request, and say whether it is within the limit.

        Args:
            user: The signed-in person making the request.

        Returns:
            Whether this request is within the person's limit for the current window.
        """
        window = int(time.time()) // self.seconds
        key = f"mvp_payments_stripe:limit:{self.name}:{user.pk}:{window}"
        cache.add(key, 0, self.seconds)
        try:
            return cache.incr(key) <= self.limit
        except ValueError:
            # The entry expired between adding and counting: a new window has begun.
            return True
