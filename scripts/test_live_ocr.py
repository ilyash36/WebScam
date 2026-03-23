#!/usr/bin/env python
"""
End-to-end тест: Vision API → парсер СТС на всех 6 фотографиях.
Запуск: python scripts/test_live_ocr.py
"""
import io
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
try:
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")
except ImportError:
    pass

from apps.website.ocr import recognize_document, mime_from_filename, parse_sts

STS_DIR = Path(r"C:\Users\iolshevskii\Desktop\СТС")


def main() -> None:
    api_key = os.environ.get("YANDEX_VISION_API_KEY", "").strip()
    folder_id = os.environ.get("YANDEX_FOLDER_ID", "").strip()

    if not api_key or not folder_id:
        print("Нужны YANDEX_VISION_API_KEY и YANDEX_FOLDER_ID в .env")
        sys.exit(1)

    images = sorted(STS_DIR.glob("*.jpg")) + sorted(STS_DIR.glob("*.png"))
    print(f"Тест Vision API + парсер СТС на {len(images)} фотографиях\n")

    for img in images:
        print(f"{'='*60}")
        print(f"Файл: {img.name}")
        with open(img, "rb") as f:
            img_bytes = f.read()
        mime = mime_from_filename(img.name)
        ta, err = recognize_document(img_bytes, api_key, folder_id, mime)
        if err:
            print(f"  ОШИБКА: {err}")
            continue
        result = parse_sts(ta)

        fields = [
            ("vehicle_vin", "VIN"),
            ("vehicle_year", "Год"),
            ("vehicle_brand", "Марка"),
            ("vehicle_model", "Модель"),
            ("vehicle_engine_power", "Мощность л.с."),
            ("vehicle_passport_number", "ПТС"),
            ("certificate_series_number", "Серия/№ СТС"),
        ]
        for field, label in fields:
            val = result.get(field, "")
            status = "✓" if val else "·"
            print(f"  {status} {label:20s}: {val!r}")
        print()


if __name__ == "__main__":
    main()
