"""Pre-train AfroLM from scratch (single-node or distributed)."""

from __future__ import annotations

import argparse
import os

import torch
import torch.distributed as dist

from afrolm.model.architecture import AfroLMConfig, AfroLMModel
from afrolm.data.tokenization import AfroLMTokenizer
from afrolm.data.datasets import LanguageDataModule
from afrolm.training.trainer import AfroTrainer, TrainingConfig
from afrolm.utils.logging import get_logger

log = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pre-train AfroLM")
    p.add_argument("--model_size", choices=["small", "base", "large"], default="base")
    p.add_argument("--data_dir",      default="data/processed/")
    p.add_argument("--tokenizer",     default="tokenizer/")
    p.add_argument("--output_dir",    default="checkpoints/")
    p.add_argument("--resume",        default=None, help="Path to checkpoint to resume from")
    p.add_argument("--max_steps",     type=int,   default=100_000)
    p.add_argument("--warmup_steps",  type=int,   default=2_000)
    p.add_argument("--batch_size",    type=int,   default=8)
    p.add_argument("--grad_accum",    type=int,   default=16)
    p.add_argument("--seq_len",       type=int,   default=2048)
    p.add_argument("--max_lr",        type=float, default=3e-4)
    p.add_argument("--min_lr",        type=float, default=3e-5)
    p.add_argument("--weight_decay",  type=float, default=0.1)
    p.add_argument("--grad_clip",     type=float, default=1.0)
    p.add_argument("--dtype",         choices=["float32", "bfloat16", "float16"], default="bfloat16")
    p.add_argument("--compile",       action="store_true")
    p.add_argument("--save_every",    type=int,   default=1_000)
    p.add_argument("--eval_every",    type=int,   default=500)
    return p.parse_args()


def setup_distributed() -> None:
    if "LOCAL_RANK" in os.environ:
        local_rank = int(os.environ["LOCAL_RANK"])
        torch.cuda.set_device(local_rank)
        dist.init_process_group(backend="nccl")


def main() -> None:
    args = parse_args()
    setup_distributed()

    # Model config
    config_cls = {"small": AfroLMConfig.small, "base": AfroLMConfig.base, "large": AfroLMConfig.large}
    model_config = config_cls[args.model_size]()

    # Update vocab size from tokenizer
    tokenizer = AfroLMTokenizer(args.tokenizer)
    model_config.vocab_size = len(tokenizer)

    model = AfroLMModel(model_config)
    n_params = model.num_parameters() / 1e6
    log.info("AfroLM-%s | %.1fM parameters", args.model_size, n_params)

    # Data
    dm = LanguageDataModule(
        data_dir=args.data_dir,
        tokenizer=tokenizer,
        seq_len=args.seq_len,
        batch_size=args.batch_size,
    )

    # Training config
    train_cfg = TrainingConfig(
        output_dir=args.output_dir,
        max_steps=args.max_steps,
        warmup_steps=args.warmup_steps,
        batch_size=args.batch_size,
        grad_accum_steps=args.grad_accum,
        seq_len=args.seq_len,
        max_lr=args.max_lr,
        min_lr=args.min_lr,
        weight_decay=args.weight_decay,
        grad_clip=args.grad_clip,
        dtype=args.dtype,
        compile=args.compile,
        save_every=args.save_every,
        eval_every=args.eval_every,
    )

    trainer = AfroTrainer(
        model=model,
        config=train_cfg,
        train_loader=dm.train_dataloader(),
        val_loader=dm.val_dataloader(),
    )

    if args.resume:
        from afrolm.utils.checkpointing import load_checkpoint
        trainer.step = load_checkpoint(args.resume, model)

    trainer.train()


if __name__ == "__main__":
    main()
