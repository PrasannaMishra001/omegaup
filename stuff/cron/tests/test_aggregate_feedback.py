'''Unit tests for the pure functions in `aggregate_feedback.py`.

Covers the cases the GSoC proposal commits to:
  * `bayesian_average`: None prior, weighted_n below CONFIDENCE,
    weighted_n at and above CONFIDENCE, all-zero votes, extreme values.
  * `get_weighting_factor`: one case per rank class, None score and a
    score exactly at a cutoff boundary.
  * `get_most_voted_tags`: below MIN_POINTS, single dominant tag, tie at
    PROBLEM_TAG_VOTE_MIN_PROPORTION, exceeds MAX_NUM_TOPICS.

These functions are pure (no DB, no IO) so no MockCursor is needed.
'''
import os
import sys
import types
import unittest

# The cron scripts are not packaged, so we extend sys.path the same way
# `aggregate_feedback.py` does for `lib/`.
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))
sys.path.insert(0, THIS_DIR)


def _install_mysql_connector_stub() -> None:
    if 'mysql' in sys.modules:
        return
    mysql_pkg = types.ModuleType('mysql')
    connector_pkg = types.ModuleType('mysql.connector')
    errorcode_mod = types.ModuleType('mysql.connector.errorcode')
    cursor_mod = types.ModuleType('mysql.connector.cursor')
    errors_mod = types.ModuleType('mysql.connector.errors')
    errorcode_mod.ER_LOCK_DEADLOCK = 1213
    errorcode_mod.ER_LOCK_WAIT_TIMEOUT = 1205

    class _Stub:
        pass

    connector_pkg.MySQLConnection = _Stub
    connector_pkg.errorcode = errorcode_mod
    connector_pkg.cursor = cursor_mod
    connector_pkg.errors = errors_mod
    cursor_mod.MySQLCursor = _Stub
    cursor_mod.MySQLCursorBuffered = _Stub
    cursor_mod.MySQLCursorDict = _Stub
    cursor_mod.MySQLCursorBufferedDict = _Stub
    errors_mod.Error = Exception
    mysql_pkg.connector = connector_pkg
    sys.modules['mysql'] = mysql_pkg
    sys.modules['mysql.connector'] = connector_pkg
    sys.modules['mysql.connector.errorcode'] = errorcode_mod
    sys.modules['mysql.connector.cursor'] = cursor_mod
    sys.modules['mysql.connector.errors'] = errors_mod

    if 'pythonjsonlogger' not in sys.modules:
        pythonjsonlogger_pkg = types.ModuleType('pythonjsonlogger')
        jsonlogger_mod = types.ModuleType('pythonjsonlogger.jsonlogger')

        import logging

        class _JsonFormatterStub(logging.Formatter):
            def __init__(self, *args: object, **kwargs: object) -> None:
                super().__init__()

        jsonlogger_mod.JsonFormatter = _JsonFormatterStub
        pythonjsonlogger_pkg.jsonlogger = jsonlogger_mod
        sys.modules['pythonjsonlogger'] = pythonjsonlogger_pkg
        sys.modules['pythonjsonlogger.jsonlogger'] = jsonlogger_mod


_install_mysql_connector_stub()

import aggregate_feedback  # noqa: E402
from fixtures import sample_data  # noqa: E402


class BayesianAverageTest(unittest.TestCase):
    '''Tests for `aggregate_feedback.bayesian_average`.'''

    def test_returns_none_when_prior_is_none(self) -> None:
        votes = sample_data.make_quality_votes([0, 0, 0, 0, 20])
        self.assertIsNone(aggregate_feedback.bayesian_average(None, votes))

    def test_returns_none_when_weighted_n_below_confidence(self) -> None:
        # weighted_n = 5, which is below CONFIDENCE = 10.
        votes = sample_data.make_quality_votes([0, 0, 5, 0, 0])
        self.assertIsNone(
            aggregate_feedback.bayesian_average(3.0, votes))

    def test_returns_value_when_weighted_n_at_confidence(self) -> None:
        # weighted_n = 10, exactly at CONFIDENCE.
        # weighted_sum = sum(i * weighted_sum_i) = 2 * 10 = 20.
        # result = (CONFIDENCE * prior + weighted_sum) /
        #         (CONFIDENCE + weighted_n)
        #        = (10 * 3.0 + 20) / (10 + 10) = 50 / 20 = 2.5
        votes = sample_data.make_quality_votes([0, 0, 10, 0, 0])
        result = aggregate_feedback.bayesian_average(3.0, votes)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertAlmostEqual(result, 2.5)

    def test_returns_value_when_weighted_n_above_confidence(self) -> None:
        # Heavy weight on score 4: weighted_n = 50, weighted_sum = 200.
        # result = (10 * 3.0 + 200) / (10 + 50) = 230 / 60 ~= 3.833
        votes = sample_data.make_quality_votes([0, 0, 0, 0, 50])
        result = aggregate_feedback.bayesian_average(3.0, votes)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertAlmostEqual(result, 230.0 / 60.0)

    def test_returns_none_when_all_zero_votes(self) -> None:
        # weighted_n = 0 < CONFIDENCE so the prior is undefined.
        votes = sample_data.make_quality_votes([0, 0, 0, 0, 0])
        self.assertIsNone(
            aggregate_feedback.bayesian_average(3.0, votes))

    def test_handles_extreme_weighted_sum(self) -> None:
        # Large but finite values must still produce a finite average,
        # bounded by the highest possible score (4.0).
        votes = sample_data.make_quality_votes([0, 0, 0, 0, 10_000])
        result = aggregate_feedback.bayesian_average(3.0, votes)
        self.assertIsNotNone(result)
        assert result is not None
        # weighted_sum = 4 * 10_000 = 40_000, weighted_n = 10_000.
        # result = (10 * 3.0 + 40_000) / (10 + 10_000) ~= 3.997
        self.assertGreater(result, 3.99)
        self.assertLess(result, 4.0)


class GetWeightingFactorTest(unittest.TestCase):
    '''Tests for `aggregate_feedback.get_weighting_factor`.'''

    def test_returns_unranked_when_score_is_none(self) -> None:
        result = aggregate_feedback.get_weighting_factor(
            None,
            sample_data.SAMPLE_RANK_CUTOFFS,
            aggregate_feedback.WEIGHTING_FACTORS,
        )
        self.assertEqual(
            result,
            aggregate_feedback.WEIGHTING_FACTORS['user-rank-unranked'],
        )

    def test_international_master_threshold(self) -> None:
        result = aggregate_feedback.get_weighting_factor(
            2000.0,
            sample_data.SAMPLE_RANK_CUTOFFS,
            aggregate_feedback.WEIGHTING_FACTORS,
        )
        self.assertEqual(
            result,
            aggregate_feedback.WEIGHTING_FACTORS[
                'user-rank-international-master'],
        )

    def test_master_threshold(self) -> None:
        result = aggregate_feedback.get_weighting_factor(
            1600.0,
            sample_data.SAMPLE_RANK_CUTOFFS,
            aggregate_feedback.WEIGHTING_FACTORS,
        )
        self.assertEqual(
            result,
            aggregate_feedback.WEIGHTING_FACTORS['user-rank-master'],
        )

    def test_expert_threshold(self) -> None:
        result = aggregate_feedback.get_weighting_factor(
            1200.0,
            sample_data.SAMPLE_RANK_CUTOFFS,
            aggregate_feedback.WEIGHTING_FACTORS,
        )
        self.assertEqual(
            result,
            aggregate_feedback.WEIGHTING_FACTORS['user-rank-expert'],
        )

    def test_specialist_threshold(self) -> None:
        result = aggregate_feedback.get_weighting_factor(
            900.0,
            sample_data.SAMPLE_RANK_CUTOFFS,
            aggregate_feedback.WEIGHTING_FACTORS,
        )
        self.assertEqual(
            result,
            aggregate_feedback.WEIGHTING_FACTORS['user-rank-specialist'],
        )

    def test_beginner_threshold(self) -> None:
        result = aggregate_feedback.get_weighting_factor(
            600.0,
            sample_data.SAMPLE_RANK_CUTOFFS,
            aggregate_feedback.WEIGHTING_FACTORS,
        )
        self.assertEqual(
            result,
            aggregate_feedback.WEIGHTING_FACTORS['user-rank-beginner'],
        )

    def test_score_exactly_at_cutoff_boundary(self) -> None:
        # Score equal to the expert cutoff (1100.0) must qualify for
        # `user-rank-expert` thanks to the `<=` predicate.
        result = aggregate_feedback.get_weighting_factor(
            1100.0,
            sample_data.SAMPLE_RANK_CUTOFFS,
            aggregate_feedback.WEIGHTING_FACTORS,
        )
        self.assertEqual(
            result,
            aggregate_feedback.WEIGHTING_FACTORS['user-rank-expert'],
        )

    def test_score_below_lowest_cutoff_returns_unranked(self) -> None:
        # If every cutoff has score > given score we should still
        # gracefully degrade to the unranked weight.
        thin_cutoffs = (
            aggregate_feedback.RankCutoff(
                classname='user-rank-expert', score=1100.0),
        )
        result = aggregate_feedback.get_weighting_factor(
            100.0,
            thin_cutoffs,
            aggregate_feedback.WEIGHTING_FACTORS,
        )
        self.assertEqual(
            result,
            aggregate_feedback.WEIGHTING_FACTORS['user-rank-unranked'],
        )

    def test_before_ac_weighting_factors_table(self) -> None:
        # Sanity check that the same lookup pipeline works for the
        # before-AC factors table the cron uses for early feedback.
        result = aggregate_feedback.get_weighting_factor(
            2000.0,
            sample_data.SAMPLE_RANK_CUTOFFS,
            aggregate_feedback.BEFORE_AC_WEIGHTING_FACTORS,
        )
        self.assertEqual(
            result,
            aggregate_feedback.BEFORE_AC_WEIGHTING_FACTORS[
                'user-rank-international-master'],
        )


class GetMostVotedTagsTest(unittest.TestCase):
    '''Tests for `aggregate_feedback.get_most_voted_tags`.'''

    def test_returns_none_below_min_points(self) -> None:
        result = aggregate_feedback.get_most_voted_tags(
            {'math': 5.0}, 5)
        self.assertIsNone(result)

    def test_single_dominant_tag_is_returned(self) -> None:
        result = aggregate_feedback.get_most_voted_tags(
            sample_data.SAMPLE_TAG_VOTES_SINGLE_DOMINANT,
            21,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(list(result), ['math'])

    def test_tie_at_min_proportion_keeps_both_tags(self) -> None:
        # graph-theory has 5 votes, math has 20. Proportion is 5/20 = 0.25
        # which equals PROBLEM_TAG_VOTE_MIN_PROPORTION, so both must
        # remain (the predicate is `>=`).
        result = aggregate_feedback.get_most_voted_tags(
            sample_data.SAMPLE_TAG_VOTES_TIE_AT_PROPORTION,
            25,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(set(result), {'math', 'graph-theory'})

    def test_returns_none_when_more_than_max_topics_match(self) -> None:
        result = aggregate_feedback.get_most_voted_tags(
            sample_data.SAMPLE_TAG_VOTES_EXCEED_LIMIT,
            50,
        )
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
