"""Run AfroLM on African NLP benchmarks and print a results table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from afrolm.model.architecture import AfroLMModel, AfroLMConfig
from afrolm.data.tokenization import AfroLMTokenizer
from afrolm.evaluation.benchmarks import BenchmarkSuite
from afrolm.utils.checkpointing import load_checkpoint
from afrolm.utils.logging import get_logger

log = get_logger(__name__)

ALL_BENCHMARKS = ["masakhanews", "masakhaner", "masakhpos", "afrixnli", "afriqa", "flores200"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate AfroLM")
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--tokenizer",  default="tokenizer/")
    p.add_argument("--data_dir",   default="data/benchmarks/")
    p.add_argument("--benchmarks", nargs="+", default=["masakhanews", "masakhaner"])
    p.add_argument("--langs",      nargs="+", default=None)
    p.add_argument("--output",     default=None, help="Save JSON results here")
    p.add_argument("--device",     default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    tokenizer = AfroLMTokenizer(args.tokenizer)
    ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    cfg = AfroLMConfig(**ckpt.get("config", {}))
    model = AfroLMModel(cfg)
    load_checkpoint(args.checkpoint, model)

    suite = BenchmarkSuite(model, tokenizer, device=args.device)
    results = suite.run(args.benchmarks, data_dir=args.data_dir, langs=args.langs)

    print("\n" + "=" * 60)
    print(f"{'Benchmark':<20} {'Lang':<8} {'Metric':<12} {'Score':>8}")
    print("-" * 60)
    for r in results:
        print(f"{r.name:<20} {r.lang:<8} {r.metric:<12} {r.score:>8.4f}")
    print("=" * 60 + "\n")

    if args.output:
        out = [{"benchmark": r.name, "lang": r.lang, "metric": r.metric, "score": r.score}
               for r in results]
        Path(args.output).write_text(json.dumps(out, indent=2))
        log.info("Results saved to %s", args.output)


if __name__ == "__main__":
    main()
