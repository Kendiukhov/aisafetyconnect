"""AfroLM decoder-only transformer with RoPE and grouped-query attention."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from afrolm.model.attention import GroupedQueryAttention
from afrolm.model.embeddings import RotaryEmbedding, apply_rotary_emb


@dataclass
class AfroLMConfig:
    vocab_size: int = 64_000
    hidden_size: int = 2048
    num_hidden_layers: int = 24
    num_attention_heads: int = 16
    num_key_value_heads: int = 8           # GQA: KV heads < query heads
    intermediate_size: int = 8192          # FFN hidden dim (≈ 4× hidden)
    max_position_embeddings: int = 4096
    rope_theta: float = 10_000.0
    rms_norm_eps: float = 1e-5
    tie_word_embeddings: bool = True
    initializer_range: float = 0.02
    dropout: float = 0.0
    attention_dropout: float = 0.0
    # Model size presets
    model_size: str = "base"

    @classmethod
    def small(cls) -> "AfroLMConfig":
        return cls(
            hidden_size=768, num_hidden_layers=12, num_attention_heads=12,
            num_key_value_heads=4, intermediate_size=3072, model_size="small",
        )

    @classmethod
    def base(cls) -> "AfroLMConfig":
        return cls(model_size="base")

    @classmethod
    def large(cls) -> "AfroLMConfig":
        return cls(
            hidden_size=4096, num_hidden_layers=32, num_attention_heads=32,
            num_key_value_heads=8, intermediate_size=16384, model_size="large",
        )

    def num_parameters(self) -> int:
        embed = self.vocab_size * self.hidden_size
        attn = (
            self.hidden_size * self.hidden_size  # Q
            + 2 * (self.hidden_size // self.num_attention_heads)
            * self.num_key_value_heads * self.hidden_size  # K, V
            + self.hidden_size * self.hidden_size  # O
        ) * self.num_hidden_layers
        ffn = (self.hidden_size * self.intermediate_size * 2  # gate + up
               + self.intermediate_size * self.hidden_size) * self.num_hidden_layers
        norm = self.hidden_size * (2 * self.num_hidden_layers + 1)
        out = 0 if self.tie_word_embeddings else self.vocab_size * self.hidden_size
        return embed + attn + ffn + norm + out


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-5) -> None:
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        norm = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return norm * self.weight


class SwiGLU(nn.Module):
    """SwiGLU feed-forward: two projections gated by silu."""

    def __init__(self, hidden: int, intermediate: int) -> None:
        super().__init__()
        self.gate_proj = nn.Linear(hidden, intermediate, bias=False)
        self.up_proj   = nn.Linear(hidden, intermediate, bias=False)
        self.down_proj = nn.Linear(intermediate, hidden, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))


class AfroLMDecoderLayer(nn.Module):
    def __init__(self, config: AfroLMConfig) -> None:
        super().__init__()
        self.self_attn = GroupedQueryAttention(config)
        self.mlp = SwiGLU(config.hidden_size, config.intermediate_size)
        self.input_layernorm = RMSNorm(config.hidden_size, eps=config.rms_norm_eps)
        self.post_attention_layernorm = RMSNorm(config.hidden_size, eps=config.rms_norm_eps)

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.Tensor] = None,
        past_key_value: Optional[tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False,
    ) -> tuple[torch.Tensor, ...]:
        residual = hidden_states
        hidden_states = self.input_layernorm(hidden_states)
        hidden_states, present_kv = self.self_attn(
            hidden_states,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_value=past_key_value,
            use_cache=use_cache,
        )
        hidden_states = residual + hidden_states
        residual = hidden_states
        hidden_states = self.post_attention_layernorm(hidden_states)
        hidden_states = self.mlp(hidden_states)
        hidden_states = residual + hidden_states
        return (hidden_states, present_kv) if use_cache else (hidden_states, None)


class AfroLMModel(nn.Module):
    """Decoder-only transformer body (no LM head)."""

    def __init__(self, config: AfroLMConfig) -> None:
        super().__init__()
        self.config = config
        self.embed_tokens = nn.Embedding(config.vocab_size, config.hidden_size, padding_idx=0)
        self.rotary_emb = RotaryEmbedding(
            config.hidden_size // config.num_attention_heads,
            max_position_embeddings=config.max_position_embeddings,
            base=config.rope_theta,
        )
        self.layers = nn.ModuleList(
            [AfroLMDecoderLayer(config) for _ in range(config.num_hidden_layers)]
        )
        self.norm = RMSNorm(config.hidden_size, eps=config.rms_norm_eps)
        self.lm_head = nn.Linear(config.hidden_size, config.vocab_size, bias=False)
        if config.tie_word_embeddings:
            self.lm_head.weight = self.embed_tokens.weight
        self._init_weights()

    def _init_weights(self) -> None:
        std = self.config.initializer_range
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, std=std)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, std=std)
                if module.padding_idx is not None:
                    module.weight.data[module.padding_idx].zero_()

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.Tensor] = None,
        past_key_values: Optional[list[tuple]] = None,
        use_cache: bool = False,
        labels: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        B, T = input_ids.shape
        if position_ids is None:
            offset = 0 if past_key_values is None else past_key_values[0][0].shape[2]
            position_ids = torch.arange(offset, offset + T, device=input_ids.device).unsqueeze(0)

        hidden_states = self.embed_tokens(input_ids)
        cos, sin = self.rotary_emb(hidden_states, seq_len=T)

        past_key_values = past_key_values or [None] * len(self.layers)
        new_cache: list[tuple] = []
        for layer, past_kv in zip(self.layers, past_key_values):
            hidden_states, present_kv = layer(
                hidden_states,
                attention_mask=attention_mask,
                position_ids=position_ids,
                past_key_value=past_kv,
                use_cache=use_cache,
            )
            if use_cache:
                new_cache.append(present_kv)

        hidden_states = self.norm(hidden_states)
        logits = self.lm_head(hidden_states)

        output: dict[str, torch.Tensor] = {"logits": logits}
        if use_cache:
            output["past_key_values"] = new_cache  # type: ignore[assignment]

        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = F.cross_entropy(
                shift_logits.view(-1, self.config.vocab_size),
                shift_labels.view(-1),
                ignore_index=-100,
            )
            output["loss"] = loss

        return output

    def num_parameters(self, trainable_only: bool = False) -> int:
        params = self.parameters() if not trainable_only else (p for p in self.parameters() if p.requires_grad)
        return sum(p.numel() for p in params)

    @classmethod
    def from_config(cls, config: AfroLMConfig) -> "AfroLMModel":
        return cls(config)
