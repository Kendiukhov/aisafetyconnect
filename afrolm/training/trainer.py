"""Distributed pretraining loop for AfroLM."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader

from afrolm.model.architecture import AfroLMModel, AfroLMConfig
from afrolm.training.optimizer import build_optimizer
from afrolm.training.scheduler import build_scheduler
from afrolm.utils.logging import get_logger
from afrolm.utils.checkpointing import save_checkpoint, load_checkpoint

log = get_logger(__name__)


@dataclass
class TrainingConfig:
    # Paths
    output_dir: str = "checkpoints/"
    data_dir: str = "data/processed/"
    tokenizer_dir: str = "tokenizer/"
    # Training
    max_steps: int = 100_000
    warmup_steps: int = 2_000
    batch_size: int = 8             # per-GPU micro-batch
    grad_accum_steps: int = 16      # effective batch = batch_size * grad_accum * n_gpus
    seq_len: int = 2048
    max_lr: float = 3e-4
    min_lr: float = 3e-5
    weight_decay: float = 0.1
    grad_clip: float = 1.0
    # Checkpointing
    save_every: int = 1_000
    eval_every: int = 500
    log_every: int = 10
    # Precision
    dtype: str = "bfloat16"
    compile: bool = False
    # Distributed
    backend: str = "nccl"


class AfroTrainer:
    def __init__(
        self,
        model: AfroLMModel,
        config: TrainingConfig,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
    ) -> None:
        self.model = model
        self.cfg = config
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.step = 0

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype = getattr(torch, config.dtype)

        self.is_ddp = dist.is_available() and dist.is_initialized()
        self.rank = dist.get_rank() if self.is_ddp else 0
        self.world_size = dist.get_world_size() if self.is_ddp else 1
        self.is_main = self.rank == 0

        model.to(self.device)
        if config.compile:
            model = torch.compile(model)  # type: ignore[assignment]
        if self.is_ddp:
            self.model = DDP(model, device_ids=[self.rank])
        else:
            self.model = model

        raw_model = self.model.module if self.is_ddp else self.model
        self.optimizer = build_optimizer(raw_model, config)
        self.scheduler = build_scheduler(self.optimizer, config)
        self.scaler = torch.cuda.amp.GradScaler(enabled=(config.dtype == "float16"))

        if self.is_main:
            log.info(
                "AfroTrainer initialised | steps=%d | device=%s | dtype=%s | world_size=%d",
                config.max_steps, self.device, config.dtype, self.world_size,
            )

    def _forward_step(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        input_ids = batch["input_ids"].to(self.device)
        labels = batch["labels"].to(self.device)
        with torch.autocast(device_type=self.device.type, dtype=self.dtype):
            out = self.model(input_ids=input_ids, labels=labels)
        return out["loss"]

    @torch.no_grad()
    def _eval(self) -> float:
        if self.val_loader is None:
            return float("nan")
        self.model.eval()
        total_loss = 0.0
        n = 0
        for batch in self.val_loader:
            loss = self._forward_step(batch)
            total_loss += loss.item()
            n += 1
            if n >= 50:
                break
        self.model.train()
        return total_loss / max(n, 1)

    def train(self) -> None:
        output_dir = Path(self.cfg.output_dir)
        if self.is_main:
            output_dir.mkdir(parents=True, exist_ok=True)

        self.model.train()
        self.optimizer.zero_grad()
        data_iter = iter(self.train_loader)
        t0 = time.time()

        while self.step < self.cfg.max_steps:
            for micro_step in range(self.cfg.grad_accum_steps):
                try:
                    batch = next(data_iter)
                except StopIteration:
                    data_iter = iter(self.train_loader)
                    batch = next(data_iter)

                loss = self._forward_step(batch) / self.cfg.grad_accum_steps
                self.scaler.scale(loss).backward()

            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.grad_clip)
            self.scaler.step(self.optimizer)
            self.scaler.update()
            self.scheduler.step()
            self.optimizer.zero_grad()
            self.step += 1

            if self.is_main and self.step % self.cfg.log_every == 0:
                dt = time.time() - t0
                lr = self.scheduler.get_last_lr()[0]
                log.info("step=%d | loss=%.4f | lr=%.2e | dt=%.2fs", self.step, loss.item(), lr, dt)
                t0 = time.time()

            if self.step % self.cfg.eval_every == 0:
                val_loss = self._eval()
                if self.is_main:
                    log.info("step=%d | val_loss=%.4f", self.step, val_loss)

            if self.is_main and self.step % self.cfg.save_every == 0:
                raw_model = self.model.module if self.is_ddp else self.model
                save_checkpoint(
                    raw_model, self.optimizer, self.step,
                    output_dir / f"ckpt_{self.step:07d}.pt",
                )

        if self.is_main:
            raw_model = self.model.module if self.is_ddp else self.model
            save_checkpoint(raw_model, self.optimizer, self.step, output_dir / "final.pt")
            log.info("Training complete. Final checkpoint saved.")
