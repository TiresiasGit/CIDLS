from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PipelineStage:
    order: int
    key: str
    title: str
    actor: str
    responsibility: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    quality_gate: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Deliverable:
    key: str
    title: str
    filename: str
    purpose: str
    acceptance_criteria: tuple[str, ...]

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ConceptPipelineSpec:
    concept_title: str
    source_image_summary: str
    stages: tuple[PipelineStage, ...]
    deliverables: tuple[Deliverable, ...]
    delivery_documents: tuple[str, ...]

    def to_dict(self):
        return {
            "concept_title": self.concept_title,
            "source_image_summary": self.source_image_summary,
            "stages": [stage.to_dict() for stage in self.stages],
            "deliverables": [item.to_dict() for item in self.deliverables],
            "delivery_documents": list(self.delivery_documents),
        }

    def deliverable_keys(self):
        return [item.key for item in self.deliverables]
