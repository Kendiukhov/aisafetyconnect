"""Cosine learning-rate scheduler with linear warmup."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from torch.optim import Optimizer
from torch.optim.lr_scheduler import LambdaLR

if TYPE_CHECKING:
    from afrolm.training.trainer import TrainingConfig


def build_scheduler(optimizer: Optimizer, config: "TrainingConfig") -> LambdaLR:
    warmup = config.warmup_steps
    total = config.max_steps
    min_ratio = config.min_lr / config.max_lr

    def lr_lambda(step: int) -> float:
        if step < warmup:
            return step / max(warmup, 1)
        progress = (step - warmup) / max(total - warmup, 1)
        cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
        return min_ratio + (1 - min_ratio) * cosine

    return LambdaLR(optimizer, lr_lambda)
