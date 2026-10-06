from typing import cast

import pytest

from microforge.application.spec.ports.outbound import SpecAdvisorPort, SpecLoaderPort
from microforge.application.spec.use_cases.recommend_spec_use_case import RecommendSpecUseCase
from microforge.domain.spec.errors import SpecValidationErrors
from microforge.domain.spec.models import SpecV1


def test_recommendation_use_case_validates_then_calls_advisor() -> None:
    spec = SpecV1.model_validate(
        {
            "models": [
                {"name": "Product", "fields": [{"name": "id", "type": "int", "primaryKey": True}]}
            ]
        }
    )
    calls: list[str] = []

    class Loader:
        def load_bytes(self, data: bytes) -> SpecV1:
            calls.append("load")
            assert data == b"spec"
            return spec

    class Advisor:
        def advise(self, loaded_spec: SpecV1) -> dict[str, object]:
            calls.append("advise")
            assert loaded_spec is spec
            return {"recommendations": []}

    use_case = RecommendSpecUseCase(
        cast(SpecLoaderPort, Loader()), cast(SpecAdvisorPort, Advisor())
    )

    assert use_case.run_bytes(b"spec") == {"recommendations": []}
    assert calls == ["load", "advise"]


def test_recommendation_use_case_does_not_advise_semantically_invalid_spec() -> None:
    invalid_spec = SpecV1.model_validate(
        {
            "api": {
                "endpoints": [
                    {
                        "name": "list-products",
                        "path": "/products",
                        "model": "Missing",
                        "filters": [{"field": "id"}],
                    }
                ]
            },
            "models": [],
        }
    )

    class Loader:
        def load_bytes(self, data: bytes) -> SpecV1:
            return invalid_spec

    class Advisor:
        def advise(self, spec: SpecV1) -> dict[str, object]:
            pytest.fail("advisor must not be called for an invalid spec")

    use_case = RecommendSpecUseCase(
        cast(SpecLoaderPort, Loader()), cast(SpecAdvisorPort, Advisor())
    )

    with pytest.raises(SpecValidationErrors):
        use_case.run_bytes(b"spec")
