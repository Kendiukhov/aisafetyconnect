"""Text cleaning and normalisation for African language corpora."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

from afrolm.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class PreprocessorConfig:
    min_length: int = 20
    max_length: int = 100_000
    deduplicate: bool = True
    normalize_unicode: bool = True
    remove_html: bool = True
    remove_urls: bool = True
    remove_emails: bool = True
    lower_ratio_threshold: float = 0.5
    digit_ratio_threshold: float = 0.3
    alpha_ratio_threshold: float = 0.5
    lang_detect: bool = False
    lang_detect_threshold: float = 0.8
    custom_filters: list[Callable[[str], bool]] = field(default_factory=list)


_HTML_TAG = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+|www\.\S+")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]+")
_MULTI_SPACE = re.compile(r" {2,}")
_MULTI_NEWLINE = re.compile(r"\n{3,}")


class TextPreprocessor:
    def __init__(self, config: PreprocessorConfig | None = None) -> None:
        self.cfg = config or PreprocessorConfig()
        self._seen: set[int] = set()

    def clean(self, text: str) -> str:
        if self.cfg.normalize_unicode:
            text = unicodedata.normalize("NFC", text)
        if self.cfg.remove_html:
            text = _HTML_TAG.sub(" ", text)
        if self.cfg.remove_urls:
            text = _URL.sub(" ", text)
        if self.cfg.remove_emails:
            text = _EMAIL.sub(" ", text)
        text = _MULTI_SPACE.sub(" ", text)
        text = _MULTI_NEWLINE.sub("\n\n", text)
        return text.strip()

    def is_quality(self, text: str) -> bool:
        if len(text) < self.cfg.min_length or len(text) > self.cfg.max_length:
            return False
        chars = [c for c in text if not c.isspace()]
        if not chars:
            return False
        alpha_ratio = sum(c.isalpha() for c in chars) / len(chars)
        digit_ratio = sum(c.isdigit() for c in chars) / len(chars)
        if alpha_ratio < self.cfg.alpha_ratio_threshold:
            return False
        if digit_ratio > self.cfg.digit_ratio_threshold:
            return False
        for fn in self.cfg.custom_filters:
            if not fn(text):
                return False
        return True

    def is_duplicate(self, text: str) -> bool:
        h = hash(text)
        if h in self._seen:
            return True
        self._seen.add(h)
        return False

    def process(self, text: str) -> str | None:
        text = self.clean(text)
        if not self.is_quality(text):
            return None
        if self.cfg.deduplicate and self.is_duplicate(text):
            return None
        return text

    def process_batch(self, texts: list[str]) -> list[str]:
        results = []
        for t in texts:
            cleaned = self.process(t)
            if cleaned is not None:
                results.append(cleaned)
        return results

    def reset_dedup(self) -> None:
        self._seen.clear()


def split_into_paragraphs(text: str, min_words: int = 5) -> list[str]:
    """Split a document into paragraph-level chunks for training."""
    paragraphs = re.split(r"\n{2,}", text)
    return [p.strip() for p in paragraphs if len(p.split()) >= min_words]


def chunk_text(text: str, chunk_size: int = 2048, overlap: int = 128) -> list[str]:
    """Split tokenised-length-aware chunks with overlap for pretraining."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks
