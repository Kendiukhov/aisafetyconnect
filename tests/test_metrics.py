"""Unit tests for evaluation metrics."""

import math

import pytest

from afrolm.evaluation.metrics import (
    compute_accuracy,
    compute_bleu,
    compute_f1_seqeval,
    compute_perplexity,
    _simple_bleu,
)


class TestPerplexity:
    def test_zero_loss(self) -> None:
        assert compute_perplexity([0.0]) == pytest.approx(1.0)

    def test_positive_loss(self) -> None:
        ppl = compute_perplexity([2.0])
        assert ppl == pytest.approx(math.exp(2.0))

    def test_empty(self) -> None:
        assert math.isinf(compute_perplexity([]))


class TestAccuracy:
    def test_perfect(self) -> None:
        assert compute_accuracy([0, 1, 2], [0, 1, 2]) == pytest.approx(1.0)

    def test_zero(self) -> None:
        assert compute_accuracy([0, 0], [1, 1]) == pytest.approx(0.0)

    def test_partial(self) -> None:
        assert compute_accuracy([0, 1], [0, 0]) == pytest.approx(0.5)

    def test_empty(self) -> None:
        assert compute_accuracy([], []) == pytest.approx(0.0)


class TestBLEU:
    def test_perfect_match(self) -> None:
        hyps = ["the cat sat on the mat"]
        refs = [["the cat sat on the mat"]]
        score = compute_bleu(hyps, refs)
        assert score > 90

    def test_no_match(self) -> None:
        hyps = ["xyz abc def"]
        refs = [["the cat sat on the mat"]]
        score = compute_bleu(hyps, refs)
        assert score == pytest.approx(0.0)

    def test_simple_bleu_fallback(self) -> None:
        score = _simple_bleu(["hello world"], ["hello world"])
        assert score > 90


class TestF1SeqEval:
    def test_perfect(self) -> None:
        preds = [["B-PER", "I-PER", "O"]]
        golds = [["B-PER", "I-PER", "O"]]
        f1 = compute_f1_seqeval(preds, golds)
        assert f1 == pytest.approx(1.0)

    def test_all_wrong(self) -> None:
        preds = [["O", "O", "O"]]
        golds = [["B-PER", "I-PER", "B-LOC"]]
        f1 = compute_f1_seqeval(preds, golds)
        assert f1 == pytest.approx(0.0)
