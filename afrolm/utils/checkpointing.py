"""Checkpoint save/load utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch.optim import Optimizer

from afrolm.utils.logging import get_logger

log = get_logger(__name__)


def save_checkpoint(
    model: nn.Module,
    optimizer: Optimizer,
    step: int,
    path: str | Path,
    extra: dict[str, Any] | None = None,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ckpt = {
        "step": step,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "config": model.config.__dict__ if hasattr(model, "config") else {},
    }
    if extra:
        ckpt.update(extra)
    torch.save(ckpt, path)
    log.info("Saved checkpoint → %s (step %d)", path, step)


def load_checkpoint(
    path: str | Path,
    model: nn.Module,
    optimizer: Optimizer | None = None,
    device: str | torch.device = "cpu",
) -> int:
    path = Path(path)
    ckpt = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    if optimizer is not None and "optimizer_state_dict" in ckpt:
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    step = ckpt.get("step", 0)
    log.info("Loaded checkpoint from %s (step %d)", path, step)
    return step
