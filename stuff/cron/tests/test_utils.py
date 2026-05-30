'''Unit tests for `utils.py`.

Covers `get_first_day_of_next_month` for every calendar month plus the
December to January year boundary, per the GSoC proposal testing plan.
'''
import datetime
import os
import sys
import unittest

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))

import utils  # noqa: E402


class GetFirstDayOfNextMonthTest(unittest.TestCase):
    '''Tests for `utils.get_first_day_of_next_month`.'''

    def _assert_next(
        self,
        current: datetime.date,
        expected: datetime.date,
    ) -> None:
        self.assertEqual(
            utils.get_first_day_of_next_month(current),
            expected,
        )

    def test_january(self) -> None:
        self._assert_next(
            datetime.date(2026, 1, 1),
            datetime.date(2026, 2, 1),
        )

    def test_february_non_leap_year(self) -> None:
        self._assert_next(
            datetime.date(2026, 2, 1),
            datetime.date(2026, 3, 1),
        )

    def test_february_leap_year(self) -> None:
        # Leap years must still return March 1st; the function only
        # depends on the month/year, not on day count.
        self._assert_next(
            datetime.date(2024, 2, 1),
            datetime.date(2024, 3, 1),
        )

    def test_march(self) -> None:
        self._assert_next(
            datetime.date(2026, 3, 1),
            datetime.date(2026, 4, 1),
        )

    def test_april(self) -> None:
        self._assert_next(
            datetime.date(2026, 4, 1),
            datetime.date(2026, 5, 1),
        )

    def test_may(self) -> None:
        self._assert_next(
            datetime.date(2026, 5, 1),
            datetime.date(2026, 6, 1),
        )

    def test_june(self) -> None:
        self._assert_next(
            datetime.date(2026, 6, 1),
            datetime.date(2026, 7, 1),
        )

    def test_july(self) -> None:
        self._assert_next(
            datetime.date(2026, 7, 1),
            datetime.date(2026, 8, 1),
        )

    def test_august(self) -> None:
        self._assert_next(
            datetime.date(2026, 8, 1),
            datetime.date(2026, 9, 1),
        )

    def test_september(self) -> None:
        self._assert_next(
            datetime.date(2026, 9, 1),
            datetime.date(2026, 10, 1),
        )

    def test_october(self) -> None:
        self._assert_next(
            datetime.date(2026, 10, 1),
            datetime.date(2026, 11, 1),
        )

    def test_november(self) -> None:
        self._assert_next(
            datetime.date(2026, 11, 1),
            datetime.date(2026, 12, 1),
        )

    def test_december_rolls_year(self) -> None:
        self._assert_next(
            datetime.date(2026, 12, 1),
            datetime.date(2027, 1, 1),
        )


if __name__ == '__main__':
    unittest.main()
