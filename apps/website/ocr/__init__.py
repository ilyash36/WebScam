"""
Модуль OCR для распознавания данных из документов СТС.

Распознавание выполняется в облачном Workflow (Vision + AI Agent).
"""
from .workflow_ocr import ocr_via_workflow

__all__ = ('ocr_via_workflow',)
