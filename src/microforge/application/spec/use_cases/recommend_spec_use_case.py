"""Spec recommendation use case."""

from microforge.application.spec.ports.inbound import RecommendSpecPort
from microforge.application.spec.ports.outbound import SpecAdvisorPort, SpecLoaderPort
from microforge.domain.spec.semantics import validate_semantics


class RecommendSpecUseCase(RecommendSpecPort):
    """Load, validate and advise on a specification."""

    def __init__(self, loader: SpecLoaderPort, advisor: SpecAdvisorPort) -> None:
        self.loader = loader
        self.advisor = advisor

    def run_bytes(self, data: bytes) -> dict[str, object]:
        """Parse the input spec, reject invalid semantics, and request advice."""
        spec = self.loader.load_bytes(data)
        validate_semantics(spec)
        return self.advisor.advise(spec)
