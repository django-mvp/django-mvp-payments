"""How many times one person may ask Stripe for something in a window."""

from unittest import mock

import pytest
from django.core.cache import cache

from mvp_payments.stripe.limits import RateLimit
from tests.factories import UserFactory


@pytest.mark.django_db
class TestRateLimit:
    def test_a_person_is_allowed_up_to_the_limit_and_refused_after(self):
        limit = RateLimit("trial", limit=3, seconds=60)
        user = UserFactory()

        answers = [limit.allows(user) for _ in range(4)]

        assert answers == [True, True, True, False]

    def test_each_person_has_their_own_count(self):
        limit = RateLimit("trial", limit=1, seconds=60)
        first, second = UserFactory(), UserFactory()
        limit.allows(first)

        assert limit.allows(second)

    def test_each_limit_has_its_own_count(self):
        user = UserFactory()
        RateLimit("one", limit=1, seconds=60).allows(user)

        assert RateLimit("other", limit=1, seconds=60).allows(user)

    def test_the_count_starts_again_in_the_next_window(self):
        limit = RateLimit("trial", limit=1, seconds=60)
        user = UserFactory()
        with mock.patch("mvp_payments.stripe.limits.time.time", return_value=600.0):
            limit.allows(user)
        with mock.patch("mvp_payments.stripe.limits.time.time", return_value=660.0):
            assert limit.allows(user)

    def test_an_entry_that_expires_between_reading_and_counting_allows(self):
        limit = RateLimit("trial", limit=1, seconds=60)
        user = UserFactory()

        with mock.patch.object(cache, "incr", side_effect=ValueError):
            assert limit.allows(user)
