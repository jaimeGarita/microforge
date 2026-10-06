import json

import httpx
import pytest

from microforge.application.spec.errors import SpecAdvisorUnavailableError
from microforge.domain.spec.models import SpecV1
from microforge.infrastructure.outbound.intelligence.jev_advisor import JEV_URL, JevAdvisor


def _spec() -> SpecV1:
    return SpecV1.model_validate(
        {
            "api": {
                "endpoints": [
                    {
                        "name": "list-products",
                        "path": "/products",
                        "model": "Product",
                        "filters": [{"field": "category_id"}],
                    }
                ]
            },
            "models": [
                {
                    "name": "Product",
                    "fields": [
                        {"name": "id", "type": "int", "primaryKey": True},
                        {"name": "category_id", "type": "int"},
                        {"name": "name", "type": "string"},
                    ],
                }
            ],
        }
    )


def test_advisor_sends_compact_candidate_state_and_maps_jev_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JEV_API_KEY", "test-secret")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "model": "jev-1.13",
                "model_version": "test",
                "answers": {
                    "candidate_0": {
                        "type": "choice",
                        "choice": "recommended",
                        "confidence": 0.9,
                        "probabilities": {
                            "recommended": 0.9,
                            "unnecessary": 0.05,
                            "human_review": 0.05,
                        },
                    }
                },
            },
        )

    result = JevAdvisor(transport=httpx.MockTransport(handler)).advise(_spec())

    assert result["recommendations"] == [
        {
            "model": "Product",
            "field": "category_id",
            "index_recommendation": "recommended",
            "confidence": 0.9,
            "probabilities": {"recommended": 0.9, "unnecessary": 0.05, "human_review": 0.05},
        }
    ]
    request = seen[0]
    assert str(request.url) == JEV_URL
    assert request.headers["Authorization"] == "Bearer test-secret"
    payload = json.loads(request.content)
    assert payload["model"] == "jev-latest"
    assert "yaml" not in payload
    candidate = payload["state"]["candidates"][0]
    assert candidate["field_name"] == "category_id"
    assert candidate["query_operations"] == ["eq"]
    assert candidate["endpoint_filters"] == ["GET /products (eq)"]
    assert candidate["named_queries"] == []
    assert candidate["relation_usage"] == []
    assert set(payload["questions"]) == {"candidate_0"}


def test_advisor_returns_empty_list_without_calling_jev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    result = JevAdvisor().advise(SpecV1())
    assert result == {"provider": "jev-ai", "model": "jev-latest", "recommendations": []}


def test_advisor_requires_api_key_when_candidates_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    with pytest.raises(SpecAdvisorUnavailableError, match="not configured"):
        JevAdvisor().advise(_spec())


def test_indexed_unique_and_primary_key_fields_are_not_sent_to_jev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JEV_API_KEY", "test-secret")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "model": "jev-latest",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "answers": {
                    "candidate_0": {
                        "type": "choice",
                        "choice": "recommended",
                        "confidence": 0.8,
                        "probabilities": {
                            "recommended": 0.8,
                            "unnecessary": 0.1,
                            "human_review": 0.1,
                        },
                    }
                },
            },
        )

    result = JevAdvisor(transport=httpx.MockTransport(handler)).advise(_spec())

    assert len(seen) == 1
    payload = json.loads(seen[0].content)
    assert [candidate["field_name"] for candidate in payload["state"]["candidates"]] == [
        "category_id"
    ]
    assert [recommendation["field"] for recommendation in result["recommendations"]] == [
        "category_id"
    ]


def test_no_jev_call_when_every_relevant_field_is_already_indexed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    spec = SpecV1.model_validate(
        {
            "api": {
                "endpoints": [
                    {
                        "name": "list-products",
                        "path": "/products",
                        "model": "Product",
                        "filters": [{"field": "id"}],
                    }
                ]
            },
            "models": [
                {
                    "name": "Product",
                    "fields": [{"name": "id", "type": "int", "primaryKey": True}],
                }
            ],
        }
    )

    result = JevAdvisor().advise(spec)

    assert result == {"provider": "jev-ai", "model": "jev-latest", "recommendations": []}


def test_advisor_maps_bad_upstream_response_to_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JEV_API_KEY", "test-secret")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502)

    transport = httpx.MockTransport(handler)
    with pytest.raises(SpecAdvisorUnavailableError, match="HTTP 502"):
        JevAdvisor(transport=transport).advise(_spec())


def test_advisor_explains_upstream_http_status_without_exposing_response_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JEV_API_KEY", "test-secret")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="secret provider diagnostic")

    transport = httpx.MockTransport(handler)

    with pytest.raises(SpecAdvisorUnavailableError, match="TypeSafe API Keys") as error:
        JevAdvisor(transport=transport).advise(_spec())

    assert "secret provider diagnostic" not in str(error.value)


def test_advisor_rejects_malformed_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JEV_API_KEY", "test-secret")
    monkeypatch.setenv("JEV_URL", "not a url")
    # Configuration is read at import time; validate the URL helper directly.
    from microforge.infrastructure.outbound.intelligence.jev_advisor import _is_valid_url

    assert not _is_valid_url("not a url")
