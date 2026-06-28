# AfroLM — African Languages Foundation Model

A from-scratch, open-source foundation language model built to natively support African languages. AfroLM covers 30+ languages across the continent, with a multilingual tokenizer trained specifically on African corpora, a modern transformer architecture, and a full training + evaluation pipeline.

## Supported Languages

| Language | ISO 639 | Region | Script |
|----------|---------|--------|--------|
| Swahili | sw | East Africa | Latin |
| Hausa | ha | West Africa | Latin / Ajami |
| Yoruba | yo | West Africa | Latin |
| Igbo | ig | West Africa | Latin |
| Zulu | zu | South Africa | Latin |
| Xhosa | xh | South Africa | Latin |
| Shona | sn | Southern Africa | Latin |
| Amharic | am | Ethiopia | Ge'ez (Ethiopic) |
| Tigrinya | ti | Ethiopia / Eritrea | Ge'ez (Ethiopic) |
| Somali | so | Horn of Africa | Latin |
| Wolof | wo | West Africa | Latin |
| Twi | tw | Ghana | Latin |
| Fula / Fulani | ff | West / Central Africa | Latin |
| Lingala | ln | Central Africa | Latin |
| Kinyarwanda | rw | East Africa | Latin |
| Luganda | lg | East Africa | Latin |
| Chichewa | ny | Southern Africa | Latin |
| Tswana | tn | Southern Africa | Latin |
| Sesotho | st | Southern Africa | Latin |
| Malagasy | mg | Madagascar | Latin |
| Oromo | om | Ethiopia / Kenya | Latin |
| Afrikaans | af | South Africa | Latin |
| Bambara | bm | West Africa | Latin |
| Kanuri | kr | Central Africa | Latin |
| Kikuyu | ki | Kenya | Latin |
| Luo | luo | Kenya / Tanzania | Latin |
| Ndebele | nd | Zimbabwe | Latin |
| Venda | ve | South Africa | Latin |
| Tshivenda | ve | South Africa | Latin |
| Nuer | nus | South Sudan | Latin |

## Architecture

AfroLM uses a decoder-only transformer (GPT-style) with several modifications optimised for African morphological richness:

- **Rotary positional embeddings (RoPE)** for better long-context handling
- **Grouped-query attention (GQA)** for efficient inference
- **SentencePiece BPE tokenizer** trained jointly on all target languages with 64 k vocabulary, sampling weighted by corpus size with α=0.7 to prevent high-resource language dominance
- **Flash Attention 2** for training speed
- Three model sizes: **Small** (125 M), **Base** (1.3 B), **Large** (7 B)

## Repository Layout

```
afrolm/              Python package (model, data, training, eval)
configs/             YAML configs for models, training, data
scripts/             CLI entry-points (prepare_data, pretrain, etc.)
tests/               Unit and integration tests
notebooks/           Exploration & demo notebooks
docker/              Dockerfile and compose files
.github/workflows/   CI/CD pipelines
```

## Quick-start

```bash
# Install
pip install -e ".[dev]"

# Download and prepare data for Swahili + Yoruba
python scripts/prepare_data.py --langs sw yo --output data/processed/

# Train the tokenizer
python scripts/train_tokenizer.py \
    --data_dir data/processed/ \
    --vocab_size 64000 \
    --output tokenizer/

# Pre-train (small model, single GPU)
python scripts/pretrain.py \
    --config configs/model/small.yaml \
    --data_dir data/processed/ \
    --tokenizer tokenizer/ \
    --output_dir checkpoints/small/

# Evaluate
python scripts/evaluate.py \
    --checkpoint checkpoints/small/final/ \
    --tokenizer tokenizer/ \
    --benchmarks afriqa,masakhanews,masakhaner
```

## Data Sources

- [CC-100](https://data.statmt.org/cc-100/) — African language web crawls
- [mC4](https://www.tensorflow.org/datasets/catalog/c4#c4multilingual) — multilingual C4 subset
- [OPUS](https://opus.nlpl.eu/) — parallel corpora for African languages
- [FLORES-200](https://github.com/facebookresearch/flores) — evaluation benchmark data
- [African Storybook](https://www.africanstorybook.org/) — children's literature
- [JW300](https://opus.nlpl.eu/JW300.php) — religious text parallel corpus
- [MasakhaNER](https://github.com/masakhane-io/masakhane-ner) — NER data
- [AfriSenti](https://github.com/afrisenti-semeval) — sentiment analysis data

## Evaluation Benchmarks

| Benchmark | Task | Languages |
|-----------|------|-----------|
| MasakhaNER | Named Entity Recognition | 21 African languages |
| MasakhaPOS | Part-of-Speech Tagging | 21 African languages |
| AfriXNLI | Natural Language Inference | 16 African languages |
| AfriQA | Question Answering | 10 African languages |
| MasakhaNews | News Topic Classification | 16 African languages |
| AfriSenti | Sentiment Analysis | 14 African languages |
| FLORES-200 | Machine Translation | 30+ African languages |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We especially welcome:
- New language corpora
- Native speaker linguistic review
- Compute donations
- Bug reports and benchmark additions

## License

Code: Apache 2.0. Model weights: CC BY 4.0. See [LICENSE](LICENSE).

## Citation

```bibtex
@misc{afrolm2024,
  title  = {AfroLM: A Foundation Language Model for African Languages},
  year   = {2024},
  url    = {https://github.com/kendiukhov/aisafetyconnect},
}
```
