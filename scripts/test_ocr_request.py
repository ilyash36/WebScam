#!/usr/bin/env python
"""POST тестового изображения на OCR эндпоинт Django."""
import argparse
import json
import re
from pathlib import Path

import requests

IMAGE_PATH = Path(r"C:\Users\iolshevskii\Desktop\СТС\photo_2024-09-18_19-21-13.jpg")
OCR_URL = "http://127.0.0.1:8000/booking/ocr-sts/"
BOOKING_URL = "http://127.0.0.1:8000/booking/"

# Mock-данные для проверки пайплайна
MOCK_OCR_RESULT = {
    "vehicle_vin": "XW8AB2CD1KA123456",
    "vehicle_year": "2019",
    "vehicle_passport_number": "77 МУ 654321",
    "certificate_series_number": "77 66 555555",
    "vehicle_brand": "Volkswagen",
    "vehicle_model": "Polo",
    "vehicle_engine_volume": "1,6",
    "vehicle_engine_power": "110",
}


def main():
    parser = argparse.ArgumentParser(description="Тест OCR через Django")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Имитация успешного ответа (без вызова Vision API)",
    )
    parser.add_argument(
        "--image",
        default=str(IMAGE_PATH),
        help="Путь к изображению",
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Ошибка: файл не найден: {image_path}")
        return 1

    if args.mock:
        print("Mock-режим: имитация успешного OCR")
        print("\n--- Распознанные данные (mock) ---")
        print(json.dumps(MOCK_OCR_RESULT, ensure_ascii=False, indent=2))
        return 0

    session = requests.Session()
    session.headers.update({"User-Agent": "TestScript/1.0"})

    # Get CSRF
    r = session.get(BOOKING_URL, timeout=10)
    m = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', r.text)
    csrf = m.group(1) if m else session.cookies.get("csrftoken", "")

    if not csrf:
        print("Ошибка: не найден CSRF токен")
        return 1

    print(f"Отправка {image_path.name} на {OCR_URL}...")
    with open(image_path, "rb") as f:
        files = {"image": ("sts.jpg", f, "image/jpeg")}
        data = {"csrfmiddlewaretoken": csrf}
        resp = session.post(OCR_URL, files=files, data=data, timeout=30)

    print(f"Статус: {resp.status_code}")
    try:
        j = resp.json()
        if j.get("success") and j.get("data"):
            print("\n--- Распознанные данные ---")
            print(json.dumps(j["data"], ensure_ascii=False, indent=2))
            return 0
        if j.get("error"):
            print("Ошибка:", j["error"])
            return 1
    except Exception as e:
        print("Response:", resp.text[:300])
        print("Parse error:", e)
    return 1


if __name__ == "__main__":
    exit(main())
