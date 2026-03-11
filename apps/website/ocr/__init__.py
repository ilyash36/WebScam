"""
Модуль OCR для распознавания данных из документов СТС/ПТС.

Yandex Vision OCR API → локальный парсер (sts_parser.py).
Время: 1–3 секунды.
"""
from .yandex_vision import recognize_document, mime_from_filename
from .sts_parser import parse_sts

__all__ = (
    'recognize_document',
    'mime_from_filename',
    'parse_sts',
)
