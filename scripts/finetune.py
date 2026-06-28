"""Fine-tune a pretrained AfroLM checkpoint on a downstream task."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from afrolm.model.architecture import AfroLMModel, AfroLMConfig
from afrolm.data.tokenization import AfroLMTokenizer
from afrolm.data.datasets import AfroDataset, _pad_collate
from afrolm.training.trainer import AfroTrainer, TrainingConfig
from afrolm.utils.checkpointing import load_checkpoint
from afrolm.utils.logging import get_logger

log = get_logger(__name__)


def load_text_file(path: Path) -> list[str]:
    if path.suffix == ".jsonl":
        return [json.loads(l).get("text", "") for l in path.read_text().splitlines() if l.strip()]
    return [l for l in path.read_text().splitlines() if l.strip()]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fine-tune AfroLM")
    p.add_argument("--checkpoint", required=True, help="Pretrained checkpoint (.pt)")
    p.add_argument("--train_file",  required=True)
    p.add_argument("--val_file",    default=None)
    p.add_argument("--tokenizer",   default="tokenizer/")
    p.add_argument("--output_dir",  default="checkpoints/finetune/")
    p.add_argument("--lang",        default=None, help="Target language code")
    p.add_argument("--max_steps",   type=int,   default=5_000)
    p.add_argument("--batch_size",  type=int,   default=4)
    p.add_argument("--max_lr",      type=float, default=1e-4)
    p.add_argument("--max_length",  type=int,   default=1024)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    tokenizer = AfroLMTokenizer(args.tokenizer)

    # Rebuild model from checkpoint
    ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    cfg = AfroLMConfig(**ckpt.get("config", {}))
    model = AfroLMModel(cfg)
    step = load_checkpoint(args.checkpoint, model)
    log.info("Loaded checkpoint from step %d", step)

    train_texts = load_text_file(Path(args.train_file))
    train_ds = AfroDataset(train_texts, tokenizer, lang=args.lang, max_length=args.max_length)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              collate_fn=lambda b: _pad_collate(b, tokenizer.PAD_ID))

    val_loader = None
    if args.val_file:
        val_texts = load_text_file(Path(args.val_file))
        val_ds = AfroDataset(val_texts, tokenizer, lang=args.lang, max_length=args.max_length)
        val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False,
                                collate_fn=lambda b: _pad_collate(b, tokenizer.PAD_ID))

    train_cfg = TrainingConfig(
        output_dir=args.output_dir,
        max_steps=args.max_steps,
        batch_size=args.batch_size,
        max_lr=args.max_lr,
        warmup_steps=min(500, args.max_steps // 10),
    )
    trainer = AfroTrainer(model, train_cfg, train_loader, val_loader)
    trainer.train()


if __name__ == "__main__":
    main()
