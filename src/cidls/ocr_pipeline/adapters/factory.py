"""
AdapterFactory: selects and instantiates OCR adapters by name.
Priority order: snipping_tool (GUI) > powertoys (GUI fallback) > winocr (native fallback)
"""
from ..exceptions import OCRPipelineError
from ..interfaces import OCRAdapter
from .fallback_ocr_adapter import PowerToysTextExtractorAdapter
from .snipping_tool_adapter import SnippingToolOCRAdapter
from .winocr_adapter import WinOCRAdapter


ADAPTER_REGISTRY: dict[str, type[OCRAdapter]] = {
    "winocr": WinOCRAdapter,
    "snipping_tool": SnippingToolOCRAdapter,
    "powertoys_text_extractor": PowerToysTextExtractorAdapter,
}

DEFAULT_ORDER = ["snipping_tool", "powertoys_text_extractor", "winocr"]


class AdapterNotFoundError(OCRPipelineError):
    pass


def build_adapter(name: str, **kwargs) -> OCRAdapter:
    cls = ADAPTER_REGISTRY.get(name)
    if cls is None:
        raise AdapterNotFoundError(
            f"unknown adapter: {name!r}. Valid: {list(ADAPTER_REGISTRY)}"
        )
    return cls(**kwargs)


def build_default_pipeline(
    preferred: str = "snipping_tool",
    fallback: str = "powertoys_text_extractor",
    template_dir: str = "fixtures/templates/snipping_tool",
) -> list[OCRAdapter]:
    adapters: list[OCRAdapter] = []
    for name in [preferred, fallback]:
        if not name:
            continue
        if name in ("snipping_tool",):
            adapters.append(SnippingToolOCRAdapter(assets_dir=template_dir))
        elif name == "winocr":
            adapters.append(WinOCRAdapter())
        elif name == "powertoys_text_extractor":
            adapters.append(PowerToysTextExtractorAdapter())
    return adapters


def list_available_adapters() -> list[dict]:
    results = []
    for name, cls in ADAPTER_REGISTRY.items():
        try:
            instance = cls()
            if hasattr(instance, "is_available"):
                available = instance.is_available()
            else:
                available = True
        except Exception:
            available = False
        results.append({"name": name, "available": available})
    return results
