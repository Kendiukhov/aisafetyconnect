"""Optimiser construction with weight-decay parameter groups."""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch
from torch.optim import AdamW

if TYPE_CHECKING:
    from afrolm.training.trainer import TrainingConfig
    from afrolm.model.architecture import AfroLMModel


def build_optimizer(model: "AfroLMModel", config: "TrainingConfig") -> AdamW:
    decay_params, no_decay_params = [], []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if param.ndim >= 2 and "embed" not in name and "norm" not in name:
            decay_params.append(param)
        else:
            no_decay_params.append(param)
    param_groups = [
        {"params": decay_params,    "weight_decay": config.weight_decay},
        {"params": no_decay_params, "weight_decay": 0.0},
    ]
    return AdamW(param_groups, lr=config.max_lr, betas=(0.9, 0.95), eps=1e-8, fused=True)
