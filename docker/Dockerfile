FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-dev python3-pip git wget curl \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    pip install --upgrade pip

WORKDIR /workspace

COPY pyproject.toml .
COPY afrolm/ afrolm/
COPY scripts/ scripts/
COPY configs/ configs/

RUN pip install -e ".[dev]"

# Pre-install flash-attn separately (needs CUDA headers)
RUN pip install flash-attn --no-build-isolation || echo "Flash Attention install failed — falling back to sdpa"

COPY . .

ENV TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=8

CMD ["python", "scripts/pretrain.py", "--help"]
