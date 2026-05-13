class OCRPipelineError(Exception):
    pass


class UnsupportedCaptureModeError(OCRPipelineError):
    pass


class AdapterActionError(OCRPipelineError):
    pass


class ClipboardTimeoutError(OCRPipelineError):
    pass


class WindowActivationError(OCRPipelineError):
    pass


class RetryExhaustedError(OCRPipelineError):
    pass


class ParseError(OCRPipelineError):
    pass


class ConversionError(OCRPipelineError):
    pass


class BrowserLaunchError(OCRPipelineError):
    pass
