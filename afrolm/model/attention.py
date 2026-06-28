"""Grouped-query attention (GQA) with RoPE and optional KV caching."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from afrolm.model.embeddings import apply_rotary_emb

if TYPE_CHECKING:
    from afrolm.model.architecture import AfroLMConfig


def repeat_kv(hidden: torch.Tensor, n_rep: int) -> torch.Tensor:
    """Expand key/value heads to match query head count (GQA)."""
    if n_rep == 1:
        return hidden
    B, H, T, D = hidden.shape
    return hidden.unsqueeze(2).expand(B, H, n_rep, T, D).reshape(B, H * n_rep, T, D)


class GroupedQueryAttention(nn.Module):
    def __init__(self, config: "AfroLMConfig") -> None:
        super().__init__()
        self.num_heads = config.num_attention_heads
        self.num_kv_heads = config.num_key_value_heads
        self.num_kv_groups = self.num_heads // self.num_kv_heads
        self.head_dim = config.hidden_size // self.num_heads
        self.hidden_size = config.hidden_size
        self.dropout = config.attention_dropout

        self.q_proj = nn.Linear(config.hidden_size, self.num_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(config.hidden_size, self.num_kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(config.hidden_size, self.num_kv_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(self.num_heads * self.head_dim, config.hidden_size, bias=False)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.Tensor] = None,
        past_key_value: Optional[tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False,
        cos: Optional[torch.Tensor] = None,
        sin: Optional[torch.Tensor] = None,
    ) -> tuple[torch.Tensor, Optional[tuple[torch.Tensor, torch.Tensor]]]:
        B, T, _ = hidden_states.shape

        q = self.q_proj(hidden_states).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(hidden_states).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(hidden_states).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)

        if cos is not None and sin is not None:
            q, k = apply_rotary_emb(q, k, cos, sin)

        if past_key_value is not None:
            k = torch.cat([past_key_value[0], k], dim=2)
            v = torch.cat([past_key_value[1], v], dim=2)

        present = (k, v) if use_cache else None

        k = repeat_kv(k, self.num_kv_groups)
        v = repeat_kv(v, self.num_kv_groups)

        # Use F.scaled_dot_product_attention (supports FlashAttention 2 backend)
        attn_out = F.scaled_dot_product_attention(
            q, k, v,
            attn_mask=attention_mask,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=(attention_mask is None),
        )
        attn_out = attn_out.transpose(1, 2).contiguous().view(B, T, self.hidden_size)
        return self.o_proj(attn_out), present
