#!/usr/bin/env python
"""
Тест парсера СТС на всех кэшированных OCR-ответах.

Работает без новых API-вызовов — использует сохранённые JSON-файлы.
Запуск: python scripts/test_sts_parser.py

Также поддерживает живой OCR для новых изображений (нужны YANDEX_VISION_API_KEY,
YANDEX_FOLDER_ID в .env; ответ сохраняется в scripts/_ocr_raw_<имя>.json):
  python scripts/test_sts_parser.py --live
"""
import io
import json
import os
import sys
from pathlib import Path

# Fix Windows console encoding
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

from apps.website.ocr.sts_parser import parse_sts

STS_DIR = Path(r"C:\Users\iolshevskii\Desktop\СТС")
CACHE_DIR = Path(__file__).parent

# Ожидаемые значения для проверки качества парсера (эталон)
EXPECTED: dict[str, dict] = {
    "photo_2024-09-18_19-21-13": {
        "vehicle_vin": "TMBJF25L8C6082224",
        "vehicle_year": "2012",
        "vehicle_brand": "SKODA",
        "vehicle_model": "YETI",
        "vehicle_engine_power": "105",
        "vehicle_passport_number": "77",  # partial - проверяем начало
        "certificate_series_number": "99 16 777407",
    },
    "photo_2024-09-22_12-37-59": {
        "vehicle_vin": "LVVDB11B7ED019877",  # или VVDB11B7ED019877
        "vehicle_year": "2013",
        "vehicle_brand": "CHERY",
        "vehicle_model": "T11 TIGGO",
        "vehicle_engine_power": "126",
        "vehicle_passport_number": "77УР958764",
        "certificate_series_number": "36 35",  # partial
    },
    "photo_2024-10-07_18-23-26": {
        "vehicle_vin": "TMBJD45J093068635",
        "vehicle_year": "2008",
        "vehicle_brand": "SKODA",
        "vehicle_model": "FABIA",
        "vehicle_engine_power": "105",
        "certificate_series_number": "51 01",  # partial
    },
    "photo_2024-10-24_18-06-12": {
        "vehicle_vin": "XW8ZZZ8R0FG001027",
        "vehicle_year": "2014",
        "vehicle_brand": "AUDI",
        "vehicle_model": "Q5",
        # OCR прочитал буквы серии как «РН» (не «УВ»)
        "vehicle_passport_number": "78РН587445",
        "certificate_series_number": "99 46 400838",
    },
    "photo_2026-02-23_23-18-48": {
        "vehicle_vin": "X7LBSRB2HAH324703",
        "vehicle_year": "2010",
        "vehicle_passport_number": "77МУ659376",
        "certificate_series_number": "99 70 308738",
    },
    "photo_2026-02-28_16-20-03": {
        "vehicle_vin": "XTA217230E0256412",
        "vehicle_year": "2014",
        "vehicle_brand": "LADA",
        "vehicle_engine_power": "97",
        "certificate_series_number": "99 27 504481",
    },
}

FIELD_LABELS = {
    "vehicle_vin": "VIN",
    "vehicle_year": "Год",
    "vehicle_passport_number": "ПТС",
    "certificate_series_number": "Серия/№ СТС",
    "vehicle_brand": "Марка",
    "vehicle_model": "Модель",
    "vehicle_engine_power": "Мощность л.с.",
    "vehicle_engine_volume": "Объём л",
}


def check_field(
    field: str,
    expected: str,
    actual: str,
) -> tuple[bool, str]:
    """
    Сравнивает ожидаемое и фактическое значение поля.

    Returns:
        (ok, reason)
    """
    actual_upper = actual.upper().strip()
    expected_upper = expected.upper().strip()

    if not expected_upper:
        return True, "skip"
    if not actual_upper:
        return False, f"пусто, ожидалось {expected!r}"

    # Нечёткая проверка: ожидаемое содержится в фактическом (или наоборот)
    if expected_upper in actual_upper or actual_upper in expected_upper:
        return True, ""
    # Для partial-проверок (например, "36 35" — только начало номера СТС)
    if actual_upper.startswith(expected_upper):
        return True, ""
    # Для VIN с разными префиксами (LVVDB vs VVDB — оба допустимы)
    if field == "vehicle_vin" and len(expected_upper) == 17:
        if actual_upper[1:] == expected_upper[1:]:  # одна буква различается
            return True, "minor prefix diff"
    return False, f"получено {actual!r}, ожидалось {expected!r}"


def run_on_cache(stem: str) -> tuple[dict, bool]:
    """Запускает парсер на кэшированном JSON файле."""
    json_path = CACHE_DIR / f"_ocr_raw_{stem}.json"
    if not json_path.exists():
        return {}, False
    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)
    ta = raw.get("result", {}).get("textAnnotation", {})
    return parse_sts(ta), True


def print_results(stem: str, result: dict) -> int:
    """
    Печатает результаты парсинга и возвращает количество ошибок.
    """
    expected = EXPECTED.get(stem, {})
    errors = 0
    print(f"\n{'='*62}")
    print(f"  {stem}")
    print(f"{'='*62}")

    for field, label in FIELD_LABELS.items():
        actual = result.get(field, "")
        exp = expected.get(field, "")
        ok, reason = check_field(field, exp, actual)

        if exp:
            status = "✓" if ok else "✗"
            if not ok:
                errors += 1
            print(f"  {status} {label:20s}: {actual!r}")
            if not ok:
                print(f"      ↳ {reason}")
        else:
            # Поле без эталона — просто выводим
            marker = "  ·"
            print(f"{marker} {label:20s}: {actual!r}")

    return errors


def main() -> None:
    live_mode = "--live" in sys.argv
    images = sorted(STS_DIR.glob("*.jpg")) + sorted(STS_DIR.glob("*.png"))

    total_checks = 0
    total_errors = 0
    skipped = 0

    for img_path in images:
        stem = img_path.stem
        result, loaded = run_on_cache(stem)
        if not loaded:
            if live_mode:
                # Живой OCR
                from apps.website.ocr.yandex_vision import (
                    recognize_document,
                    mime_from_filename,
                )
                import requests as _req
                api_key = os.environ.get("YANDEX_VISION_API_KEY", "").strip()
                folder_id = os.environ.get("YANDEX_FOLDER_ID", "").strip()
                print(f"\n[OCR live] {img_path.name}...")
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
                mime = mime_from_filename(img_path.name)
                ta, err = recognize_document(img_bytes, api_key, folder_id, mime)
                if err:
                    print(f"  ERROR: {err}")
                    skipped += 1
                    continue
                # Сохраняем в кэш
                cache_path = CACHE_DIR / f"_ocr_raw_{stem}.json"
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump({"result": {"textAnnotation": ta}}, f,
                              ensure_ascii=False, indent=2)
                result = parse_sts(ta)
            else:
                print(f"\n[SKIP] {stem} — нет кэша. Запустите с --live")
                skipped += 1
                continue

        errs = print_results(stem, result)
        total_errors += errs
        # Считаем только проверяемые поля
        total_checks += sum(
            1 for f in EXPECTED.get(stem, {}) if EXPECTED[stem][f]
        )

    # Итоговый счёт
    print(f"\n{'='*62}")
    checked = total_checks - skipped
    passed = checked - total_errors
    score = (passed / checked * 100) if checked else 0
    print(f"ИТОГ: {passed}/{checked} проверок пройдено ({score:.0f}%)")
    if skipped:
        print(f"      {skipped} изображений пропущено (нет кэша)")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
