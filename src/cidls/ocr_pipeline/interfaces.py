from abc import ABC, abstractmethod


class OCRAdapter(ABC):
    name = "base"

    @abstractmethod
    def supports(self, capture_request):
        raise NotImplementedError

    @abstractmethod
    def extract(self, capture_request, evidence_run):
        raise NotImplementedError
