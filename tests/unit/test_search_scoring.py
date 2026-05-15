"""Unit tests for hybrid search scoring arithmetic — no embeddings needed."""

import pytest

from some_vault_some_mcp.tools.search import _SEMANTIC_WEIGHT, _KW_WEIGHT, _BOOST_FACTOR


# Pure arithmetic: 70/30 weighting with 1.2x boost
def _score(sem: float, kw: float) -> float:
    combined = sem * _SEMANTIC_WEIGHT + kw * _KW_WEIGHT
    if sem > 0 and kw > 0:
        combined *= _BOOST_FACTOR
    return min(combined, 1.0)


def test_semantic_only():
    s = _score(0.8, 0.0)
    assert abs(s - 0.8 * 0.7) < 1e-9


def test_keyword_only():
    s = _score(0.0, 0.8)
    assert abs(s - 0.8 * 0.3) < 1e-9


def test_both_gets_boost():
    s_boost = _score(0.5, 0.5)
    s_no_boost = 0.5 * 0.7 + 0.5 * 0.3
    assert s_boost > s_no_boost
    assert abs(s_boost - s_no_boost * 1.2) < 1e-9


def test_weights_sum_to_one_without_boost():
    s = _score(1.0, 1.0)
    # Boost applied but clamped to 1.0
    assert abs(s - 1.0) < 1e-9


def test_full_semantic_no_kw_no_boost():
    s = _score(1.0, 0.0)
    assert abs(s - 0.7) < 1e-9


def test_score_never_exceeds_one():
    """Even with boost, score should be clamped to 1.0."""
    s = _score(1.0, 1.0)
    assert s <= 1.0


def test_zero_scores():
    assert _score(0.0, 0.0) == 0.0
