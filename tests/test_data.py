"""Unit tests for data processing utilities."""

import pytest

from afrolm.data.preprocessing import TextPreprocessor, PreprocessorConfig, split_into_paragraphs, chunk_text
from afrolm.data.sources import AFRICAN_LANGUAGES, language_info


class TestTextPreprocessor:
    def setup_method(self) -> None:
        self.pp = TextPreprocessor()

    def test_removes_html(self) -> None:
        result = self.pp.clean("<p>Hello world</p>")
        assert "<p>" not in result
        assert "Hello world" in result

    def test_removes_urls(self) -> None:
        result = self.pp.clean("Visit https://example.com for more info")
        assert "https://" not in result

    def test_removes_emails(self) -> None:
        result = self.pp.clean("Contact user@example.com today")
        assert "@" not in result

    def test_normalises_spaces(self) -> None:
        result = self.pp.clean("hello   world")
        assert "  " not in result

    def test_rejects_too_short(self) -> None:
        assert self.pp.process("hi") is None

    def test_rejects_mostly_digits(self) -> None:
        assert self.pp.process("1234567890 1234567890 1234567890") is None

    def test_accepts_good_text(self) -> None:
        text = "Swahili ni lugha ya Afrika Mashariki ambayo inazungumzwa na watu wengi."
        result = self.pp.process(text)
        assert result is not None

    def test_deduplication(self) -> None:
        text = "This is a sentence that is long enough to pass quality filters."
        first = self.pp.process(text)
        second = self.pp.process(text)
        assert first is not None
        assert second is None  # duplicate

    def test_batch(self) -> None:
        texts = [
            "A" * 5,   # too short
            "Lugha ya Kiswahili ni muhimu sana kwa mawasiliano ya Afrika Mashariki.",
            "Lugha ya Kiswahili ni muhimu sana kwa mawasiliano ya Afrika Mashariki.",  # dup
        ]
        result = self.pp.process_batch(texts)
        assert len(result) == 1


class TestSplitParagraphs:
    def test_splits_on_double_newline(self) -> None:
        text = "First paragraph here.\n\nSecond paragraph here with more words."
        parts = split_into_paragraphs(text)
        assert len(parts) == 2

    def test_filters_short_paragraphs(self) -> None:
        text = "Hi.\n\nThis is a longer paragraph that should be kept."
        parts = split_into_paragraphs(text, min_words=5)
        assert len(parts) == 1


class TestChunkText:
    def test_produces_chunks(self) -> None:
        words = " ".join(["word"] * 1000)
        chunks = chunk_text(words, chunk_size=100, overlap=10)
        assert len(chunks) > 1

    def test_overlap(self) -> None:
        words = " ".join([str(i) for i in range(200)])
        chunks = chunk_text(words, chunk_size=50, overlap=10)
        last_of_first = chunks[0].split()[-10:]
        first_of_second = chunks[1].split()[:10]
        assert last_of_first == first_of_second


class TestLanguageSources:
    def test_all_codes_known(self) -> None:
        for code in AFRICAN_LANGUAGES:
            info = language_info(code)
            assert "name" in info
            assert "script" in info
            assert "region" in info

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError):
            language_info("xx")

    def test_at_least_twenty_languages(self) -> None:
        assert len(AFRICAN_LANGUAGES) >= 20
