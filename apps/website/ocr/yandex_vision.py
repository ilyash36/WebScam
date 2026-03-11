"""
Прямой вызов Yandex Vision OCR API для распознавания СТС/ПТС.

Endpoint: https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText
Документация: https://yandex.cloud/ru/docs/vision/ocr/api-ref/TextRecognition/recognize
"""
import base64
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

OCR_ENDPOINT = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"

# Таймаут в секундах — Vision OCR обычно отвечает за 1–3 сек
REQUEST_TIMEOUT = 20


def recognize_document(
    image_bytes: bytes,
    api_key: str,
    folder_id: str,
    mime_type: str = "JPEG",
) -> tuple[Optional[dict], Optional[str]]:
    """
    Вызывает Yandex Vision OCR API и возвращает textAnnotation.

    Args:
        image_bytes: Содержимое изображения в байтах.
        api_key: API-ключ Yandex Cloud.
        folder_id: ID каталога Yandex Cloud.
        mime_type: Тип изображения: "JPEG", "PNG" или "PDF".

    Returns:
        (text_annotation_dict, error_message) — ровно одно из полей None.
    """
    content_b64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "mimeType": mime_type,
        "languageCodes": ["ru", "en"],
        "content": content_b64,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {api_key}",
        "x-folder-id": folder_id,
    }
    try:
        resp = requests.post(
            OCR_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.warning("Vision OCR request failed: %s", exc)
        return (None, str(exc))

    if resp.status_code != 200:
        msg = f"Vision OCR HTTP {resp.status_code}: {resp.text[:200]}"
        logger.warning(msg)
        return (None, msg)

    try:
        data = resp.json()
    except Exception as exc:
        return (None, f"Vision OCR response parse error: {exc}")

    ta = (
        data.get("result", {}).get("textAnnotation")
        or data.get("textAnnotation")
    )
    if ta is None:
        return (None, "Vision OCR: нет textAnnotation в ответе")

    return (ta, None)


def mime_from_filename(filename: str) -> str:
    """
    Определяет MIME-тип по имени файла.

    Args:
        filename: Имя файла.

    Returns:
        Строка MIME-типа для Vision OCR API.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {"png": "PNG", "pdf": "PDF"}.get(ext, "JPEG")
