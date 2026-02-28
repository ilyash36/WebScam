#!/usr/bin/env python
"""
Тест Workflow OCR: Vision + AI Agent в облачном workflow.

Запуск:
    python scripts/test_workflow_ocr.py путь/к/изображению.jpg

Workflow принимает image_base64. Vision и парсинг выполняются в workflow.
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path

# Загрузка .env из корня проекта
_project_root = Path(__file__).resolve().parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Тест Workflow OCR")
    parser.add_argument("image", help="Путь к изображению (СТС, ПТС)")
    parser.add_argument(
        "--url",
        default=os.environ.get("WORKFLOW_OCR_URL"),
        help="URL workflow (или WORKFLOW_OCR_URL в .env)",
    )
    parser.add_argument(
        "--secret",
        default=os.environ.get("WORKFLOW_OCR_SECRET"),
        help="Секрет (или WORKFLOW_OCR_SECRET в .env)",
    )
    args = parser.parse_args()

    url = (args.url or "").strip()
    secret = (args.secret or "").strip()
    if not url:
        print("Ошибка: укажите WORKFLOW_OCR_URL в .env или --url")
        sys.exit(1)
    if not secret:
        print("Ошибка: укажите WORKFLOW_OCR_SECRET в .env или --secret")
        sys.exit(1)

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Ошибка: файл не найден: {image_path}")
        sys.exit(1)

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {"image_base64": image_base64, "secret": secret}

    print(f"Отправка запроса на {url[:60]}...")
    print(f"Размер изображения: {len(image_bytes)} байт")

    try:
        import requests
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        print(f"\nСтатус: {resp.status_code}")
        try:
            data = resp.json()
            print(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception:
            print(resp.text[:500])
        if resp.status_code >= 400:
            sys.exit(1)
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
