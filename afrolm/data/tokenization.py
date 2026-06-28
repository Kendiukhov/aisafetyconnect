"""SentencePiece BPE tokenizer wrapper for AfroLM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union

import sentencepiece as spm
from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import Whitespace

from afrolm.utils.logging import get_logger

log = get_logger(__name__)

SPECIAL_TOKENS = [
    "<pad>", "<unk>", "<bos>", "<eos>", "<mask>",
    "<sep>", "<cls>",
]
LANG_TOKENS = [
    "<lang:sw>", "<lang:ha>", "<lang:yo>", "<lang:ig>",
    "<lang:zu>", "<lang:xh>", "<lang:sn>", "<lang:am>",
    "<lang:ti>", "<lang:so>", "<lang:wo>", "<lang:tw>",
    "<lang:ff>", "<lang:ln>", "<lang:rw>", "<lang:lg>",
    "<lang:ny>", "<lang:tn>", "<lang:st>", "<lang:mg>",
    "<lang:om>", "<lang:af>", "<lang:bm>", "<lang:ki>",
    "<lang:luo>", "<lang:nd>", "<lang:ve>", "<lang:nus>",
    "<lang:kr>", "<lang:ss>",
]
ALL_SPECIAL_TOKENS = SPECIAL_TOKENS + LANG_TOKENS


class AfroLMTokenizer:
    """Multilingual BPE tokenizer with per-language prepend tokens."""

    PAD_ID = 0
    UNK_ID = 1
    BOS_ID = 2
    EOS_ID = 3
    MASK_ID = 4

    def __init__(self, tokenizer_path: str | Path) -> None:
        tokenizer_path = Path(tokenizer_path)
        self._sp = spm.SentencePieceProcessor()
        self._sp.Load(str(tokenizer_path / "tokenizer.model"))
        with open(tokenizer_path / "tokenizer_config.json") as f:
            cfg = json.load(f)
        self.vocab_size: int = cfg["vocab_size"]
        self._token2id: dict[str, int] = cfg["special_tokens"]
        self._id2token: dict[int, str] = {v: k for k, v in self._token2id.items()}

    # ------------------------------------------------------------------
    # Core encode / decode
    # ------------------------------------------------------------------

    def encode(
        self,
        text: str,
        lang: str | None = None,
        add_bos: bool = True,
        add_eos: bool = True,
        max_length: int | None = None,
    ) -> list[int]:
        ids: list[int] = self._sp.EncodeAsIds(text)
        if add_bos:
            ids = [self.BOS_ID] + ids
        if lang is not None:
            lang_tok = f"<lang:{lang}>"
            lang_id = self._token2id.get(lang_tok)
            if lang_id is not None:
                ids = [lang_id] + ids
        if add_eos:
            ids = ids + [self.EOS_ID]
        if max_length is not None:
            ids = ids[:max_length]
        return ids

    def decode(self, ids: list[int], skip_special: bool = True) -> str:
        if skip_special:
            ids = [i for i in ids if i not in self._id2token]
        return self._sp.DecodeIds(ids)

    def encode_batch(
        self,
        texts: list[str],
        lang: str | None = None,
        pad: bool = True,
        max_length: int | None = None,
    ) -> dict[str, list[list[int]]]:
        encoded = [self.encode(t, lang=lang, max_length=max_length) for t in texts]
        if pad:
            max_len = max(len(e) for e in encoded)
            attention_mask = []
            for e in encoded:
                pad_len = max_len - len(e)
                attention_mask.append([1] * len(e) + [0] * pad_len)
                e.extend([self.PAD_ID] * pad_len)
        else:
            attention_mask = [[1] * len(e) for e in encoded]
        return {"input_ids": encoded, "attention_mask": attention_mask}

    # ------------------------------------------------------------------
    # Vocabulary utilities
    # ------------------------------------------------------------------

    def token_to_id(self, token: str) -> int:
        special = self._token2id.get(token)
        if special is not None:
            return special
        return self._sp.PieceToId(token)

    def id_to_token(self, idx: int) -> str:
        special = self._id2token.get(idx)
        if special is not None:
            return special
        return self._sp.IdToPiece(idx)

    def __len__(self) -> int:
        return self.vocab_size

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def train(
        cls,
        input_files: list[str | Path],
        output_dir: str | Path,
        vocab_size: int = 64_000,
        character_coverage: float = 0.9999,
        sampling_alpha: float = 0.7,
    ) -> "AfroLMTokenizer":
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        model_prefix = str(output_dir / "tokenizer")
        input_str = ",".join(str(f) for f in input_files)
        user_defined = ",".join(ALL_SPECIAL_TOKENS)
        spm.SentencePieceTrainer.Train(
            input=input_str,
            model_prefix=model_prefix,
            vocab_size=vocab_size,
            character_coverage=character_coverage,
            model_type="bpe",
            user_defined_symbols=user_defined,
            pad_id=0,
            unk_id=1,
            bos_id=2,
            eos_id=3,
            pad_piece="<pad>",
            unk_piece="<unk>",
            bos_piece="<bos>",
            eos_piece="<eos>",
            input_sentence_size=10_000_000,
            shuffle_input_sentence=True,
            normalization_rule_name="nmt_nfkc_cf",
        )
        # Build id mapping for special tokens from the trained model
        sp = spm.SentencePieceProcessor()
        sp.Load(model_prefix + ".model")
        special_map = {tok: sp.PieceToId(tok) for tok in ALL_SPECIAL_TOKENS}
        cfg = {
            "vocab_size": sp.GetPieceSize(),
            "special_tokens": special_map,
            "sampling_alpha": sampling_alpha,
        }
        with open(output_dir / "tokenizer_config.json", "w") as f:
            json.dump(cfg, f, indent=2)
        log.info("Tokenizer saved to %s (vocab_size=%d)", output_dir, cfg["vocab_size"])
        return cls(output_dir)
