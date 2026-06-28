"""Evaluation harness for African NLP benchmarks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import torch
from tqdm import tqdm

from afrolm.model.architecture import AfroLMModel
from afrolm.data.tokenization import AfroLMTokenizer
from afrolm.evaluation.metrics import (
    compute_perplexity,
    compute_bleu,
    compute_f1_seqeval,
    compute_accuracy,
)
from afrolm.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class BenchmarkResult:
    name: str
    lang: str
    metric: str
    score: float
    details: dict[str, Any]

    def __str__(self) -> str:
        return f"{self.name}/{self.lang} | {self.metric}={self.score:.4f}"


class BenchmarkSuite:
    """Run multiple African NLP benchmarks and collect results."""

    SUPPORTED = ["masakhanews", "masakhaner", "masakhpos", "afrixnli", "afriqa", "flores200"]

    def __init__(
        self,
        model: AfroLMModel,
        tokenizer: AfroLMTokenizer,
        device: str | torch.device = "cpu",
    ) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.device = torch.device(device)
        self.model.to(self.device)
        self.model.eval()

    def run(
        self,
        benchmarks: list[str],
        data_dir: str | Path,
        langs: list[str] | None = None,
    ) -> list[BenchmarkResult]:
        results = []
        for name in benchmarks:
            if name not in self.SUPPORTED:
                log.warning("Unknown benchmark %s, skipping", name)
                continue
            fn = getattr(self, f"_run_{name.replace('-', '_')}", None)
            if fn is None:
                log.warning("No runner for %s", name)
                continue
            results.extend(fn(Path(data_dir) / name, langs=langs))
        return results

    # ------------------------------------------------------------------
    # Per-benchmark runners
    # ------------------------------------------------------------------

    def _run_masakhanews(
        self, data_dir: Path, langs: list[str] | None = None
    ) -> list[BenchmarkResult]:
        results = []
        for lang_dir in sorted(data_dir.glob("*")):
            if not lang_dir.is_dir():
                continue
            lang = lang_dir.name
            if langs and lang not in langs:
                continue
            test_file = lang_dir / "test.jsonl"
            if not test_file.exists():
                log.warning("Missing %s", test_file)
                continue
            examples = [json.loads(l) for l in test_file.read_text().splitlines()]
            preds, golds = self._classify_news(examples, lang)
            acc = compute_accuracy(preds, golds)
            results.append(BenchmarkResult("masakhanews", lang, "accuracy", acc, {}))
            log.info("MasakhaNews/%s accuracy=%.4f", lang, acc)
        return results

    def _run_masakhaner(
        self, data_dir: Path, langs: list[str] | None = None
    ) -> list[BenchmarkResult]:
        results = []
        for lang_dir in sorted(data_dir.glob("*")):
            if not lang_dir.is_dir():
                continue
            lang = lang_dir.name
            if langs and lang not in langs:
                continue
            test_file = lang_dir / "test.txt"
            if not test_file.exists():
                continue
            sentences, gold_labels = self._load_conll(test_file)
            pred_labels = self._tag_ner(sentences, lang)
            f1 = compute_f1_seqeval(pred_labels, gold_labels)
            results.append(BenchmarkResult("masakhaner", lang, "f1", f1, {}))
            log.info("MasakhaNER/%s F1=%.4f", lang, f1)
        return results

    def _run_flores200(
        self, data_dir: Path, langs: list[str] | None = None
    ) -> list[BenchmarkResult]:
        results = []
        src_file = data_dir / "devtest" / "devtest.eng_Latn"
        if not src_file.exists():
            log.warning("FLORES-200 source file not found at %s", src_file)
            return results
        sources = src_file.read_text().splitlines()
        for lang_file in sorted((data_dir / "devtest").glob("devtest.*")):
            lang = lang_file.suffix.lstrip(".")
            if langs and lang not in langs:
                continue
            if lang == "eng_Latn":
                continue
            refs = lang_file.read_text().splitlines()
            hyps = self._translate(sources, lang)
            bleu = compute_bleu(hyps, [refs])
            results.append(BenchmarkResult("flores200", lang, "bleu", bleu, {}))
            log.info("FLORES-200/%s BLEU=%.2f", lang, bleu)
        return results

    # ------------------------------------------------------------------
    # Model-calling helpers (stub implementations — override for real eval)
    # ------------------------------------------------------------------

    @torch.no_grad()
    def _classify_news(
        self, examples: list[dict], lang: str
    ) -> tuple[list[int], list[int]]:
        """Zero-shot classification via perplexity over label prompts."""
        LABELS = ["politics", "sports", "health", "entertainment", "business", "technology"]
        preds, golds = [], []
        for ex in tqdm(examples, desc=f"MasakhaNews/{lang}"):
            text = ex.get("text", ex.get("headline", ""))
            gold = ex.get("label", 0)
            scores = []
            for label in LABELS:
                prompt = f"[{label}] {text}"
                ids = self.tokenizer.encode(prompt, lang=lang, max_length=256)
                t = torch.tensor([ids], device=self.device)
                out = self.model(input_ids=t, labels=t)
                scores.append(out["loss"].item())
            preds.append(int(scores.index(min(scores))))
            golds.append(int(gold))
        return preds, golds

    @torch.no_grad()
    def _tag_ner(
        self, sentences: list[list[str]], lang: str
    ) -> list[list[str]]:
        """Greedy token-by-token NER tagging (demonstration stub)."""
        return [["O"] * len(s) for s in sentences]

    @torch.no_grad()
    def _translate(self, sources: list[str], tgt_lang: str, max_new: int = 128) -> list[str]:
        """Greedy decoding for machine translation."""
        outputs = []
        for src in tqdm(sources[:100], desc=f"FLORES/{tgt_lang}"):
            prompt = f"Translate to {tgt_lang}: {src}"
            ids = self.tokenizer.encode(prompt, lang=None, max_length=128)
            t = torch.tensor([ids], device=self.device)
            generated = list(ids)
            for _ in range(max_new):
                inp = torch.tensor([generated], device=self.device)
                out = self.model(input_ids=inp)
                next_id = out["logits"][0, -1].argmax().item()
                if next_id == self.tokenizer.EOS_ID:
                    break
                generated.append(next_id)
            outputs.append(self.tokenizer.decode(generated[len(ids):]))
        return outputs

    @staticmethod
    def _load_conll(path: Path) -> tuple[list[list[str]], list[list[str]]]:
        sentences, labels = [], []
        words, tags = [], []
        for line in path.read_text().splitlines():
            if line.strip() == "":
                if words:
                    sentences.append(words)
                    labels.append(tags)
                words, tags = [], []
            else:
                parts = line.split()
                words.append(parts[0])
                tags.append(parts[-1])
        if words:
            sentences.append(words)
            labels.append(tags)
        return sentences, labels
