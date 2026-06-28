"""Train the AfroLM SentencePiece BPE tokenizer on all language data."""

from __future__ import annotations

import argparse
import random
import tempfile
from pathlib import Path

from afrolm.data.sources import AFRICAN_LANGUAGES, iter_raw_texts
from afrolm.data.preprocessing import TextPreprocessor, PreprocessorConfig
from afrolm.data.tokenization import AfroLMTokenizer
from afrolm.utils.logging import get_logger

log = get_logger(__name__)

# UnigramLM-style α-sampling weights: smaller corpora get boosted
ALPHA = 0.7


def compute_sample_sizes(
    raw_dir: Path,
    langs: list[str],
    total_lines: int = 5_000_000,
) -> dict[str, int]:
    """Determine per-language sampling budget using size^α weighting."""
    sizes: dict[str, float] = {}
    for lang in langs:
        n = sum(1 for _ in iter_raw_texts(raw_dir, lang))
        sizes[lang] = max(n, 1)
    total_weight = sum(v ** ALPHA for v in sizes.values())
    return {
        lang: int(total_lines * (sizes[lang] ** ALPHA) / total_weight)
        for lang in langs
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train AfroLM tokenizer")
    parser.add_argument("--data_dir", default="data/raw/", help="Raw text directory")
    parser.add_argument("--output", default="tokenizer/", help="Output directory")
    parser.add_argument("--vocab_size", type=int, default=64_000)
    parser.add_argument("--langs", nargs="+", default=list(AFRICAN_LANGUAGES.keys()))
    parser.add_argument("--total_lines", type=int, default=5_000_000,
                        help="Total lines sampled across all languages")
    args = parser.parse_args()

    raw_dir = Path(args.data_dir)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    preprocessor = TextPreprocessor(PreprocessorConfig(deduplicate=True))
    sample_sizes = compute_sample_sizes(raw_dir, args.langs, args.total_lines)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        for lang, budget in sample_sizes.items():
            log.info("Sampling %d lines for %s", budget, lang)
            collected = 0
            for line in iter_raw_texts(raw_dir, lang):
                cleaned = preprocessor.process(line)
                if cleaned and len(cleaned.split()) >= 4:
                    tmp.write(cleaned + "\n")
                    collected += 1
                    if collected >= budget:
                        break
            log.info("  → %d lines collected", collected)

    log.info("Training tokenizer (vocab_size=%d)…", args.vocab_size)
    AfroLMTokenizer.train(
        input_files=[tmp_path],
        output_dir=output_dir,
        vocab_size=args.vocab_size,
    )
    tmp_path.unlink(missing_ok=True)
    log.info("Tokenizer saved to %s", output_dir)


if __name__ == "__main__":
    main()
