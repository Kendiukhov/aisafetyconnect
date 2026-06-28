"""Data source definitions and download utilities for African language corpora."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import requests
from tqdm import tqdm

from afrolm.utils.logging import get_logger

log = get_logger(__name__)

AFRICAN_LANGUAGES: dict[str, dict] = {
    "sw": {"name": "Swahili",      "script": "Latin",    "region": "East Africa"},
    "ha": {"name": "Hausa",        "script": "Latin",    "region": "West Africa"},
    "yo": {"name": "Yoruba",       "script": "Latin",    "region": "West Africa"},
    "ig": {"name": "Igbo",         "script": "Latin",    "region": "West Africa"},
    "zu": {"name": "Zulu",         "script": "Latin",    "region": "South Africa"},
    "xh": {"name": "Xhosa",        "script": "Latin",    "region": "South Africa"},
    "sn": {"name": "Shona",        "script": "Latin",    "region": "Southern Africa"},
    "am": {"name": "Amharic",      "script": "Ethiopic", "region": "East Africa"},
    "ti": {"name": "Tigrinya",     "script": "Ethiopic", "region": "East Africa"},
    "so": {"name": "Somali",       "script": "Latin",    "region": "East Africa"},
    "wo": {"name": "Wolof",        "script": "Latin",    "region": "West Africa"},
    "tw": {"name": "Twi",          "script": "Latin",    "region": "West Africa"},
    "ff": {"name": "Fula",         "script": "Latin",    "region": "West Africa"},
    "ln": {"name": "Lingala",      "script": "Latin",    "region": "Central Africa"},
    "rw": {"name": "Kinyarwanda",  "script": "Latin",    "region": "East Africa"},
    "lg": {"name": "Luganda",      "script": "Latin",    "region": "East Africa"},
    "ny": {"name": "Chichewa",     "script": "Latin",    "region": "Southern Africa"},
    "tn": {"name": "Tswana",       "script": "Latin",    "region": "Southern Africa"},
    "st": {"name": "Sesotho",      "script": "Latin",    "region": "Southern Africa"},
    "mg": {"name": "Malagasy",     "script": "Latin",    "region": "Indian Ocean"},
    "om": {"name": "Oromo",        "script": "Latin",    "region": "East Africa"},
    "af": {"name": "Afrikaans",    "script": "Latin",    "region": "South Africa"},
    "bm": {"name": "Bambara",      "script": "Latin",    "region": "West Africa"},
    "ki": {"name": "Kikuyu",       "script": "Latin",    "region": "East Africa"},
    "luo": {"name": "Luo",         "script": "Latin",    "region": "East Africa"},
    "nd": {"name": "Ndebele",      "script": "Latin",    "region": "Southern Africa"},
    "ve": {"name": "Venda",        "script": "Latin",    "region": "South Africa"},
    "nus": {"name": "Nuer",        "script": "Latin",    "region": "East Africa"},
    "kr": {"name": "Kanuri",       "script": "Latin",    "region": "Central Africa"},
    "ss": {"name": "Swati",        "script": "Latin",    "region": "South Africa"},
}


@dataclass
class DataSource:
    name: str
    url_template: str
    languages: list[str]
    license: str
    description: str
    checksum_file: str = ""
    extra_headers: dict = field(default_factory=dict)

    def url_for(self, lang: str) -> str:
        return self.url_template.format(lang=lang)


DATA_SOURCES: list[DataSource] = [
    DataSource(
        name="cc100",
        url_template="https://data.statmt.org/cc-100/{lang}.txt.xz",
        languages=["sw", "ha", "yo", "ig", "zu", "am", "so", "af", "rw", "mg", "om", "sn"],
        license="CC-BY-SA 4.0",
        description="Common Crawl 100 — web text for 100 languages",
    ),
    DataSource(
        name="opus_jw300",
        url_template="https://opus.nlpl.eu/download.php?f=JW300/v1/{lang}.txt.gz",
        languages=["sw", "yo", "ig", "zu", "xh", "ny", "tn", "st", "rw", "ln", "wo"],
        license="CC BY 4.0",
        description="JW300 religious parallel text corpus",
    ),
    DataSource(
        name="opus_tanzil",
        url_template="https://opus.nlpl.eu/download.php?f=Tanzil/v1/{lang}.txt.gz",
        languages=["ha", "so", "am"],
        license="CC BY 4.0",
        description="Quranic translations",
    ),
    DataSource(
        name="african_storybook",
        url_template="https://www.africanstorybook.org/api/books?language={lang}",
        languages=["sw", "yo", "ig", "zu", "xh", "ny", "tn", "st", "rw", "lg", "am"],
        license="CC BY 4.0",
        description="African Storybook children's literature",
    ),
    DataSource(
        name="masakhane_mt",
        url_template="https://raw.githubusercontent.com/masakhane-io/masakhane-mt/master/MT-data/{lang}/train.{lang}",
        languages=["sw", "yo", "ig", "zu", "xh", "ny", "tn", "st", "rw", "lg", "wo", "sn"],
        license="CC BY 4.0",
        description="Masakhane machine translation monolingual data",
    ),
]


def _download_file(url: str, dest: Path, headers: dict | None = None, retries: int = 3) -> Path:
    headers = headers or {}
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, stream=True, timeout=60)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True, desc=dest.name
            ) as bar:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
                    bar.update(len(chunk))
            return dest
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            log.warning("Download failed (%s), retrying in %ds…", exc, wait)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def download_source(
    source: DataSource,
    lang: str,
    output_dir: Path,
    skip_existing: bool = True,
) -> Path | None:
    if lang not in source.languages:
        log.debug("Language %s not in source %s", lang, source.name)
        return None
    url = source.url_for(lang)
    ext = Path(url.split("?")[0]).suffixes
    filename = f"{source.name}_{lang}{''.join(ext)}"
    dest = output_dir / filename
    if skip_existing and dest.exists():
        log.info("Skipping %s (already exists)", dest)
        return dest
    log.info("Downloading %s → %s", url, dest)
    return _download_file(url, dest, headers=source.extra_headers)


def iter_raw_texts(raw_dir: Path, lang: str) -> Iterator[str]:
    """Yield lines from all downloaded raw files for a language."""
    import lzma
    import gzip

    for path in sorted(raw_dir.glob(f"*_{lang}.*")):
        log.info("Reading %s", path)
        opener = {".xz": lzma.open, ".gz": gzip.open}.get(path.suffix, open)
        with opener(path, "rt", encoding="utf-8", errors="replace") as f:
            yield from f


def language_info(lang: str) -> dict:
    if lang not in AFRICAN_LANGUAGES:
        raise ValueError(f"Unknown language code '{lang}'. Supported: {list(AFRICAN_LANGUAGES)}")
    return AFRICAN_LANGUAGES[lang]
