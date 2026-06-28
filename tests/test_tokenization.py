"""Unit tests for tokenizer utilities (uses mock SentencePiece)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from afrolm.data.tokenization import (
    AfroLMTokenizer,
    ALL_SPECIAL_TOKENS,
    LANG_TOKENS,
    SPECIAL_TOKENS,
)


@pytest.fixture
def mock_tokenizer_dir(tmp_path: Path) -> Path:
    """Create a minimal mock tokenizer directory."""
    # Build a fake special-token mapping
    special = {tok: i for i, tok in enumerate(ALL_SPECIAL_TOKENS)}
    cfg = {"vocab_size": len(ALL_SPECIAL_TOKENS) + 1000, "special_tokens": special}
    (tmp_path / "tokenizer_config.json").write_text(json.dumps(cfg))
    # The .model file is required by SentencePieceProcessor.Load() — we'll patch it
    (tmp_path / "tokenizer.model").write_bytes(b"")
    return tmp_path


class TestAfroLMTokenizer:
    def test_special_tokens_defined(self) -> None:
        assert "<pad>" in SPECIAL_TOKENS
        assert "<bos>" in SPECIAL_TOKENS
        assert "<eos>" in SPECIAL_TOKENS
        assert "<lang:sw>" in LANG_TOKENS
        assert "<lang:am>" in LANG_TOKENS

    def test_all_special_tokens_count(self) -> None:
        assert len(ALL_SPECIAL_TOKENS) == len(SPECIAL_TOKENS) + len(LANG_TOKENS)

    @patch("afrolm.data.tokenization.spm.SentencePieceProcessor")
    def test_encode_decode_roundtrip(self, mock_sp_cls: MagicMock, mock_tokenizer_dir: Path) -> None:
        mock_sp = MagicMock()
        mock_sp.EncodeAsIds.return_value = [100, 200, 300]
        mock_sp.DecodeIds.return_value = "hello world"
        mock_sp.PieceToId.side_effect = lambda tok: ALL_SPECIAL_TOKENS.index(tok) if tok in ALL_SPECIAL_TOKENS else 999
        mock_sp_cls.return_value = mock_sp

        tok = AfroLMTokenizer(mock_tokenizer_dir)
        ids = tok.encode("hello world", lang=None, add_bos=True, add_eos=True)
        assert ids[0] == AfroLMTokenizer.BOS_ID
        assert ids[-1] == AfroLMTokenizer.EOS_ID
        assert 100 in ids

        text = tok.decode(ids)
        assert isinstance(text, str)

    @patch("afrolm.data.tokenization.spm.SentencePieceProcessor")
    def test_lang_token_prepended(self, mock_sp_cls: MagicMock, mock_tokenizer_dir: Path) -> None:
        mock_sp = MagicMock()
        mock_sp.EncodeAsIds.return_value = [500]
        mock_sp.PieceToId.side_effect = lambda tok: ALL_SPECIAL_TOKENS.index(tok) if tok in ALL_SPECIAL_TOKENS else 999
        mock_sp_cls.return_value = mock_sp

        tok = AfroLMTokenizer(mock_tokenizer_dir)
        ids_no_lang = tok.encode("text", lang=None, add_bos=False, add_eos=False)
        ids_with_lang = tok.encode("text", lang="sw", add_bos=False, add_eos=False)
        assert len(ids_with_lang) == len(ids_no_lang) + 1

    @patch("afrolm.data.tokenization.spm.SentencePieceProcessor")
    def test_encode_batch_pads(self, mock_sp_cls: MagicMock, mock_tokenizer_dir: Path) -> None:
        mock_sp = MagicMock()
        mock_sp.EncodeAsIds.side_effect = [[100], [200, 201, 202]]
        mock_sp.PieceToId.side_effect = lambda tok: ALL_SPECIAL_TOKENS.index(tok) if tok in ALL_SPECIAL_TOKENS else 999
        mock_sp_cls.return_value = mock_sp

        tok = AfroLMTokenizer(mock_tokenizer_dir)
        out = tok.encode_batch(["a", "b c d"], pad=True)
        lengths = [len(ids) for ids in out["input_ids"]]
        assert len(set(lengths)) == 1  # all same length after padding
