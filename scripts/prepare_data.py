"""Download, clean, and shard African language corpora for pretraining."""

from __future__ import annotations

import argparse
import array
import random
from pathlib import Path

from tqdm import tqdm

from afrolm.data.sources import DATA_SOURCES, AFRICAN_LANGUAGES, download_source, iter_raw_texts
from afrolm.data.preprocessing import TextPreprocessor, PreprocessorConfig, split_into_paragraphs
from afrolm.data.tokenization import AfroLMTokenizer
from afrolm.utils.logging import get_logger

log = get_logger(__name__)

SHARD_SIZE = 10_000_000  # tokens per shard


def tokenise_and_shard(
    texts: list[str],
    tokenizer: AfroLMTokenizer,
    lang: str,
    output_dir: Path,
    split: str = "train",
    shard_size: int = SHARD_SIZE,
) -> int:
    shard_dir = output_dir / split
    shard_dir.mkdir(parents=True, exist_ok=True)
    buf: array.array = array.array("i")
    shard_idx = 0
    total = 0

    def flush():
        nonlocal shard_idx
        path = shard_dir / f"{lang}_{shard_idx:05d}.bin"
        with open(path, "wb") as f:
            buf.tofile(f)
        log.info("Wrote shard %s (%d tokens)", path, len(buf))
        buf[:] = array.array("i")
        shard_idx += 1

    for text in tqdm(texts, desc=f"Tokenising {lang}"):
        ids = tokenizer.encode(text, lang=lang, add_bos=True, add_eos=True)
        buf.extend(ids)
        total += len(ids)
        if len(buf) >= shard_size:
            flush()

    if buf:
        flush()
    return total


def prepare_language(
    lang: str,
    raw_dir: Path,
    output_dir: Path,
    tokenizer: AfroLMTokenizer,
    val_fraction: float = 0.001,
    skip_download: bool = False,
) -> None:
    if not skip_download:
        for source in DATA_SOURCES:
            try:
                download_source(source, lang, raw_dir)
            except Exception as exc:
                log.warning("Failed to download %s/%s: %s", source.name, lang, exc)

    preprocessor = TextPreprocessor(PreprocessorConfig(deduplicate=True))
    all_texts: list[str] = []

    for line in iter_raw_texts(raw_dir, lang):
        cleaned = preprocessor.process(line)
        if cleaned:
            all_texts.extend(split_into_paragraphs(cleaned))

    if not all_texts:
        log.warning("No texts found for language %s", lang)
        return

    random.shuffle(all_texts)
    split_idx = max(1, int(len(all_texts) * val_fraction))
    val_texts = all_texts[:split_idx]
    train_texts = all_texts[split_idx:]

    train_tokens = tokenise_and_shard(train_texts, tokenizer, lang, output_dir, "train")
    val_tokens = tokenise_and_shard(val_texts, tokenizer, lang, output_dir, "val")
    log.info(
        "Language %s: %d train tokens, %d val tokens",
        lang, train_tokens, val_tokens,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare AfroLM training data")
    parser.add_argument("--langs", nargs="+", default=list(AFRICAN_LANGUAGES.keys()),
                        help="Language codes to process")
    parser.add_argument("--raw_dir", default="data/raw/", help="Raw download directory")
    parser.add_argument("--output", default="data/processed/", help="Output directory for shards")
    parser.add_argument("--tokenizer", default="tokenizer/", help="Tokenizer directory")
    parser.add_argument("--val_fraction", type=float, default=0.001)
    parser.add_argument("--skip_download", action="store_true")
    args = parser.parse_args()

    tokenizer = AfroLMTokenizer(args.tokenizer)
    raw_dir = Path(args.raw_dir)
    output_dir = Path(args.output)

    for lang in args.langs:
        if lang not in AFRICAN_LANGUAGES:
            log.warning("Unknown language %s, skipping", lang)
            continue
        log.info("Processing language: %s (%s)", lang, AFRICAN_LANGUAGES[lang]["name"])
        prepare_language(
            lang, raw_dir, output_dir, tokenizer,
            val_fraction=args.val_fraction,
            skip_download=args.skip_download,
        )

    log.info("Data preparation complete.")


if __name__ == "__main__":
    main()
