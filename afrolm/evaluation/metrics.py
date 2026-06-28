"""Evaluation metrics for AfroLM benchmarks."""

from __future__ import annotations

import math
from typing import Sequence

import torch
import torch.nn.functional as F


def compute_perplexity(
    losses: list[float],
) -> float:
    avg_loss = sum(losses) / len(losses) if losses else float("inf")
    return math.exp(avg_loss)


def compute_accuracy(preds: list[int], golds: list[int]) -> float:
    if not preds:
        return 0.0
    return sum(p == g for p, g in zip(preds, golds)) / len(preds)


def compute_bleu(
    hypotheses: list[str],
    references: list[list[str]],
) -> float:
    try:
        import sacrebleu
        result = sacrebleu.corpus_bleu(hypotheses, references)
        return result.score
    except ImportError:
        return _simple_bleu(hypotheses, references[0])


def _simple_bleu(hypotheses: list[str], references: list[str], max_n: int = 4) -> float:
    """Minimal BLEU implementation (sacrebleu not installed)."""
    from collections import Counter
    import math

    def ngrams(tokens: list[str], n: int) -> Counter:
        return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))

    clipped_prec = []
    for n in range(1, max_n + 1):
        num, denom = 0, 0
        for hyp, ref in zip(hypotheses, references):
            h_toks = hyp.split()
            r_toks = ref.split()
            h_ng = ngrams(h_toks, n)
            r_ng = ngrams(r_toks, n)
            clipped = {k: min(v, r_ng[k]) for k, v in h_ng.items()}
            num += sum(clipped.values())
            denom += sum(h_ng.values())
        clipped_prec.append(num / max(denom, 1))

    if any(p == 0 for p in clipped_prec):
        return 0.0
    log_bleu = sum(math.log(p) for p in clipped_prec) / max_n
    hyp_len = sum(len(h.split()) for h in hypotheses)
    ref_len = sum(len(r.split()) for r in references)
    bp = 1.0 if hyp_len >= ref_len else math.exp(1 - ref_len / max(hyp_len, 1))
    return 100 * bp * math.exp(log_bleu)


def compute_f1_seqeval(
    preds: list[list[str]],
    golds: list[list[str]],
) -> float:
    try:
        from seqeval.metrics import f1_score
        return f1_score(golds, preds)
    except ImportError:
        return _token_f1(preds, golds)


def _token_f1(preds: list[list[str]], golds: list[list[str]]) -> float:
    tp = fp = fn = 0
    for ps, gs in zip(preds, golds):
        for p, g in zip(ps, gs):
            if g != "O":
                if p == g:
                    tp += 1
                else:
                    fn += 1
            elif p != "O":
                fp += 1
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)
