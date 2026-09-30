"""Download only the OCR language files used in this pilot, with SHA-256 checks."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import requests

from pilot.collect import OUT


MODELS = {
    "fast_vie": (
        "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/vie.traineddata",
        "79df64caf7bcfb2a27df5042ecb6121e196eada34da774956995747636d5bfa1",
        OUT / "tessdata" / "vie.traineddata",
    ),
    "best_vie": (
        "https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/vie.traineddata",
        "b6b49293d95d0b6dbd8780174627e82c75be957b6f4ed9862155540d6b00bb45",
        OUT / "tessdata_best" / "vie.traineddata",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--best", action="store_true", help="Also fetch slower quality-comparison model")
    args = parser.parse_args()
    names = ("fast_vie", "best_vie") if args.best else ("fast_vie",)
    for name in names:
        url, expected, path = MODELS[name]
        if path.exists():
            data = path.read_bytes()
        else:
            response = requests.get(url, timeout=(10, 120))
            response.raise_for_status()
            data = response.content
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise ValueError(f"Unexpected {name} SHA-256: {actual}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print(f"{name}: {len(data)} bytes, sha256={actual}")


if __name__ == "__main__":
    main()
