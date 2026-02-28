"""
Вызов Workflow OCR (Vision + AI Agent) с polling результата.

Распознавание и парсинг выполняются в облачном Workflow.
"""
import json
import logging
import re
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

POLL_INTERVAL = 1.5
POLL_TIMEOUT = 45


def _extract_json_from_text(text: str) -> Optional[dict]:
    """Извлекает JSON из текста (агент может вернуть markdown или обёртку)."""
    if not text or not text.strip():
        return None
    text = text.strip()
    start = text.find('{')
    if start >= 0:
        depth = 0
        for i, c in enumerate(text[start:], start):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _workflow_output_to_form_data(output: dict) -> dict:
    """Преобразует вывод агента в формат формы (to_dict)."""
    return {
        'vehicle_vin': output.get('vehicle_vin', ''),
        'vehicle_year': str(output.get('vehicle_year', '')),
        'vehicle_license_plate': output.get('vehicle_license_plate', ''),
        'vehicle_color': output.get('vehicle_color', ''),
        'vehicle_passport_number': output.get(
            'vehicle_passport_number',
            output.get('vehicle_body_number', ''),
        ),
        'certificate_series_number': output.get(
            'certificate_series_number', ''
        ),
        'vehicle_brand': output.get('vehicle_brand', ''),
        'vehicle_model': output.get('vehicle_model', ''),
        'vehicle_engine_volume': output.get('vehicle_engine_volume', ''),
        'vehicle_engine_power': str(output.get('vehicle_engine_power', '')),
    }


def ocr_via_workflow(
    image_base64: str,
    workflow_url: str,
    secret: str,
    api_key: str,
    folder_id: str,
) -> tuple[Optional[dict], Optional[str]]:
    """
    Запускает workflow: Vision + AI Agent внутри workflow.

    Django передаёт image_base64. При ошибке fallback в Django.

    Returns:
        (data_dict, error_message)
    """
    payload = {'image_base64': image_base64, 'secret': secret}
    try:
        resp = requests.post(
            workflow_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30,
        )
    except requests.RequestException as e:
        logger.warning("Workflow start failed: %s", e)
        return (None, str(e))

    if resp.status_code != 200:
        return (None, f"Workflow {resp.status_code}: {resp.text[:200]}")

    try:
        data = resp.json()
    except Exception:
        return (None, "Workflow вернул не JSON")

    execution_id = data.get('executionId')
    if not execution_id:
        return (None, "Нет executionId в ответе")

    # Poll за результатом
    base = workflow_url.rsplit('/start', 1)[0]
    get_url = f"{base.rsplit('/execution', 1)[0]}/execution/{execution_id}"
    params = {}
    if folder_id:
        params['folderId'] = folder_id
    headers = {}
    if api_key:
        headers['Authorization'] = f'Api-Key {api_key}'
    if folder_id:
        headers['x-folder-id'] = folder_id

    deadline = time.monotonic() + POLL_TIMEOUT
    last_err = ""

    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL)
        try:
            r = requests.get(
                get_url,
                params=params or None,
                headers=headers or None,
                timeout=10,
            )
        except requests.RequestException as e:
            last_err = str(e)
            continue

        if r.status_code != 200:
            last_err = f"GET {r.status_code}"
            continue

        try:
            exec_data = r.json()
        except Exception:
            continue

        status = exec_data.get('status', '').upper()
        if status == 'SUCCEEDED':
            output = exec_data.get('output') or exec_data.get('result') or {}
            if isinstance(output, str):
                parsed = _extract_json_from_text(output)
                if parsed:
                    return (_workflow_output_to_form_data(parsed), None)
                return (None, "Не удалось извлечь JSON из ответа агента")
            if isinstance(output, dict):
                # Может быть вложенная структура
                if 'output' in output:
                    output = output['output']
                if isinstance(output, str):
                    parsed = _extract_json_from_text(output)
                    if parsed:
                        return (_workflow_output_to_form_data(parsed), None)
                elif isinstance(output, dict):
                    return (_workflow_output_to_form_data(output), None)
            return (None, "Неожиданный формат output")
        if status in ('FAILED', 'CANCELLED'):
            return (None, exec_data.get('error', {}).get('message', status))

    return (None, last_err or "Таймаут ожидания результата")
