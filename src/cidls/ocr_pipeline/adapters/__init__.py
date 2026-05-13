from .fallback_ocr_adapter import PowerToysTextExtractorAdapter
from .factory import AdapterNotFoundError, build_adapter, build_default_pipeline, list_available_adapters
from .snipping_tool_adapter import SnippingToolOCRAdapter
from .winocr_adapter import WinOCRAdapter, WinOCRUnavailableError

__all__ = [
    "PowerToysTextExtractorAdapter",
    "SnippingToolOCRAdapter",
    "WinOCRAdapter",
    "WinOCRUnavailableError",
    "AdapterNotFoundError",
    "build_adapter",
    "build_default_pipeline",
    "list_available_adapters",
]
