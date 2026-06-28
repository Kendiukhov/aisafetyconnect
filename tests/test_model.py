"""Unit tests for the AfroLM model architecture."""

import pytest
import torch

from afrolm.model.architecture import AfroLMConfig, AfroLMModel
from afrolm.model.embeddings import RotaryEmbedding, apply_rotary_emb


@pytest.fixture
def tiny_config() -> AfroLMConfig:
    return AfroLMConfig(
        vocab_size=1000,
        hidden_size=64,
        num_hidden_layers=2,
        num_attention_heads=4,
        num_key_value_heads=2,
        intermediate_size=128,
        max_position_embeddings=128,
    )


@pytest.fixture
def tiny_model(tiny_config: AfroLMConfig) -> AfroLMModel:
    return AfroLMModel(tiny_config)


class TestAfroLMConfig:
    def test_small_preset(self) -> None:
        cfg = AfroLMConfig.small()
        assert cfg.model_size == "small"
        assert cfg.hidden_size == 768
        assert cfg.num_key_value_heads < cfg.num_attention_heads

    def test_base_preset(self) -> None:
        cfg = AfroLMConfig.base()
        assert cfg.hidden_size == 2048

    def test_large_preset(self) -> None:
        cfg = AfroLMConfig.large()
        assert cfg.hidden_size == 4096

    def test_num_parameters_estimate(self) -> None:
        cfg = AfroLMConfig.small()
        est = cfg.num_parameters()
        assert 100_000_000 < est < 200_000_000


class TestAfroLMModel:
    def test_forward_shape(self, tiny_model: AfroLMModel, tiny_config: AfroLMConfig) -> None:
        B, T = 2, 16
        input_ids = torch.randint(0, tiny_config.vocab_size, (B, T))
        out = tiny_model(input_ids)
        assert "logits" in out
        assert out["logits"].shape == (B, T, tiny_config.vocab_size)

    def test_loss_computed_with_labels(self, tiny_model: AfroLMModel, tiny_config: AfroLMConfig) -> None:
        B, T = 2, 16
        input_ids = torch.randint(0, tiny_config.vocab_size, (B, T))
        labels = input_ids.clone()
        out = tiny_model(input_ids, labels=labels)
        assert "loss" in out
        assert out["loss"].item() > 0

    def test_kv_cache(self, tiny_model: AfroLMModel, tiny_config: AfroLMConfig) -> None:
        input_ids = torch.randint(0, tiny_config.vocab_size, (1, 8))
        out_no_cache = tiny_model(input_ids)
        out_with_cache = tiny_model(input_ids, use_cache=True)
        assert "past_key_values" in out_with_cache
        # Logits should match
        torch.testing.assert_close(
            out_no_cache["logits"], out_with_cache["logits"], atol=1e-4, rtol=1e-4
        )

    def test_num_parameters(self, tiny_model: AfroLMModel) -> None:
        n = tiny_model.num_parameters()
        assert n > 0

    def test_gradient_flows(self, tiny_model: AfroLMModel, tiny_config: AfroLMConfig) -> None:
        input_ids = torch.randint(0, tiny_config.vocab_size, (1, 8))
        labels = input_ids.clone()
        out = tiny_model(input_ids, labels=labels)
        out["loss"].backward()
        grad_norms = [p.grad.norm().item() for p in tiny_model.parameters() if p.grad is not None]
        assert len(grad_norms) > 0
        assert all(g == g for g in grad_norms)  # no NaNs


class TestRotaryEmbeddings:
    def test_output_shape(self) -> None:
        rope = RotaryEmbedding(dim=32, max_position_embeddings=64)
        x = torch.randn(1, 4, 16, 32)
        cos, sin = rope(x, seq_len=16)
        assert cos.shape[-1] == 32
        assert sin.shape[-1] == 32

    def test_apply_rotary_preserves_shape(self) -> None:
        B, H, T, D = 2, 4, 8, 32
        q = torch.randn(B, H, T, D)
        k = torch.randn(B, H, T, D)
        rope = RotaryEmbedding(D, max_position_embeddings=T)
        cos, sin = rope(q, seq_len=T)
        q_rot, k_rot = apply_rotary_emb(q, k, cos, sin)
        assert q_rot.shape == q.shape
        assert k_rot.shape == k.shape
