# Contributing to AfroLM

Thank you for your interest in AfroLM. This project relies on community contributions — especially native speakers, linguists, and ML researchers with experience in African languages.

## Ways to contribute

### Language data
- Curate or link to high-quality monolingual corpora for a language not yet in our pipeline
- Review existing data for quality, offensive content, or cultural mismatch
- Provide transliteration tables for languages with multiple scripts (e.g. Hausa Ajami ↔ Latin)

### Model and training
- Identify bugs or improvements in tokenization, model architecture, or training scripts
- Benchmark the model on a new downstream task
- Provide compute resources (contact us first)

### Code
- Fix an open issue
- Add a new benchmark runner under `afrolm/evaluation/`
- Improve documentation or test coverage

## Development setup

```bash
git clone https://github.com/kendiukhov/aisafetyconnect.git
cd aisafetyconnect
pip install -e ".[dev]"
pre-commit install
```

## Pull request process

1. Open an issue to discuss your change if it's non-trivial
2. Fork the repository and work on a feature branch
3. Add or update tests for your change
4. Run `ruff check .` and `pytest` locally
5. Submit the pull request — a maintainer will review within a week

## Commit style

```
type(scope): short description

Optional longer description.
```

Types: `feat`, `fix`, `data`, `eval`, `docs`, `test`, `chore`

## Code of conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/) v2.1. We especially value respectful, constructive engagement from the African NLP community.

## Language-specific guidelines

- Tone marks and diacritics must be preserved (e.g. Yoruba `ẹ`, `ọ`, `ṣ`, tones)
- Amharic/Tigrinya Ethiopic script must not be lowercased or decomposed
- Data from religious texts (JW300, Tanzil) should be labeled accordingly so users can opt out
- Do not include data that was scraped without consent from personal communications
