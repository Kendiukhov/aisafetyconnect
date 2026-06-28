"""PyTorch Dataset and DataModule for AfroLM pre-training."""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Iterator

import torch
from torch.utils.data import Dataset, DataLoader, IterableDataset

from afrolm.data.tokenization import AfroLMTokenizer
from afrolm.utils.logging import get_logger

log = get_logger(__name__)


class TokenisedShardDataset(IterableDataset):
    """Streams pre-tokenised binary shards (int32 arrays) from disk."""

    def __init__(
        self,
        shard_dir: Path,
        seq_len: int = 2048,
        shuffle_shards: bool = True,
    ) -> None:
        self.shards = sorted(Path(shard_dir).glob("*.bin"))
        if not self.shards:
            raise FileNotFoundError(f"No .bin shards found in {shard_dir}")
        self.seq_len = seq_len
        self.shuffle_shards = shuffle_shards

    def _iter_shard(self, path: Path) -> Iterator[torch.Tensor]:
        data = torch.frombuffer(path.read_bytes(), dtype=torch.int32).long()
        n = len(data) // (self.seq_len + 1)
        for i in range(n):
            chunk = data[i * (self.seq_len + 1) : (i + 1) * (self.seq_len + 1)]
            yield chunk

    def __iter__(self) -> Iterator[dict[str, torch.Tensor]]:
        shards = list(self.shards)
        if self.shuffle_shards:
            random.shuffle(shards)
        for shard in shards:
            for chunk in self._iter_shard(shard):
                x = chunk[:-1]
                y = chunk[1:]
                yield {"input_ids": x, "labels": y}


class AfroDataset(Dataset):
    """In-memory dataset for fine-tuning on smaller datasets."""

    def __init__(
        self,
        texts: list[str],
        tokenizer: AfroLMTokenizer,
        lang: str | None = None,
        max_length: int = 2048,
    ) -> None:
        self.tokenizer = tokenizer
        self.lang = lang
        self.max_length = max_length
        self.examples: list[dict[str, torch.Tensor]] = []
        for text in texts:
            ids = tokenizer.encode(text, lang=lang, max_length=max_length)
            if len(ids) < 2:
                continue
            input_ids = torch.tensor(ids[:-1], dtype=torch.long)
            labels = torch.tensor(ids[1:], dtype=torch.long)
            self.examples.append({"input_ids": input_ids, "labels": labels})

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return self.examples[idx]


def _pad_collate(batch: list[dict[str, torch.Tensor]], pad_id: int = 0) -> dict[str, torch.Tensor]:
    max_len = max(x["input_ids"].size(0) for x in batch)
    input_ids, labels, masks = [], [], []
    for x in batch:
        L = x["input_ids"].size(0)
        pad = max_len - L
        input_ids.append(torch.cat([x["input_ids"], torch.full((pad,), pad_id, dtype=torch.long)]))
        labels.append(torch.cat([x["labels"], torch.full((pad,), -100, dtype=torch.long)]))
        masks.append(torch.cat([torch.ones(L, dtype=torch.long), torch.zeros(pad, dtype=torch.long)]))
    return {
        "input_ids": torch.stack(input_ids),
        "labels": torch.stack(labels),
        "attention_mask": torch.stack(masks),
    }


class LanguageDataModule:
    """Manages train/validation data loaders for multi-language pretraining."""

    def __init__(
        self,
        data_dir: str | Path,
        tokenizer: AfroLMTokenizer,
        seq_len: int = 2048,
        batch_size: int = 8,
        num_workers: int = 4,
        val_fraction: float = 0.001,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.tokenizer = tokenizer
        self.seq_len = seq_len
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.val_fraction = val_fraction

    def train_dataloader(self) -> DataLoader:
        ds = TokenisedShardDataset(self.data_dir / "train", self.seq_len, shuffle_shards=True)
        return DataLoader(
            ds,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            pin_memory=True,
        )

    def val_dataloader(self) -> DataLoader:
        ds = TokenisedShardDataset(self.data_dir / "val", self.seq_len, shuffle_shards=False)
        return DataLoader(
            ds,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            pin_memory=True,
        )
