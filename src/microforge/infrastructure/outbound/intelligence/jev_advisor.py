"""Jev SystemOne adapter for database-index recommendations."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

from microforge.application.spec.errors import SpecAdvisorUnavailableError
from microforge.application.spec.ports.outbound import SpecAdvisorPort
from microforge.domain.spec.models import ModelSpec, SpecV1
from microforge.infrastructure.outbound.intelligence.jev_models import (
    JevChoiceQuestion,
    JevIndexCandidate,
    JevIndexState,
    JevRequest,
    JevResponse,
)

load_dotenv()

JEV_URL = os.getenv("JEV_URL", "https://api.typesafe.ai/v1/systemone")
JEV_MODEL = os.getenv("JEV_MODEL", "jev-latest")
MAX_QUESTIONS_PER_REQUEST = int(os.getenv("MAX_QUESTIONS_PER_REQUEST", "20"))
logger = logging.getLogger(__name__)
_CRITERIA = {
    "recommended": "An index is likely to improve common filtering or relation lookups.",
    "unnecessary": "An index is unlikely to provide a useful performance benefit.",
    "human_review": "There is not enough information; a developer should decide.",
}


class JevAdvisor(SpecAdvisorPort):
    """Provide index recommendations for a validated spec using Jev."""

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def advise(self, spec: SpecV1) -> dict[str, object]:
        """Ask Jev about relevant fields, returning a stable API response."""
        candidates = list(_index_candidates(spec))
        if not candidates:
            return {"provider": "jev-ai", "model": JEV_MODEL, "recommendations": []}

        api_key = os.environ.get("JEV_API_KEY")
        if not api_key:
            raise SpecAdvisorUnavailableError("Jev recommendations are not configured.")
        if not _is_valid_url(JEV_URL):
            raise SpecAdvisorUnavailableError("JEV_URL must be an absolute HTTP(S) URL.")

        recommendations: list[dict[str, object]] = []
        try:
            with httpx.Client(transport=self._transport, timeout=15.0) as client:
                for batch in _batches(candidates):
                    request = _request_for_batch(batch, model=JEV_MODEL)
                    response = client.post(
                        JEV_URL,
                        headers={"Authorization": f"Bearer {api_key}"},
                        json=request.model_dump(mode="json"),
                    )
                    response.raise_for_status()
                    jev_response = JevResponse.model_validate(response.json())
                    expected_keys = {f"candidate_{index}" for index in range(len(batch))}
                    if jev_response.answers.keys() != expected_keys:
                        raise ValueError("Jev returned a mismatched set of answers.")
                    for index, candidate in enumerate(batch):
                        answer = jev_response.answers[f"candidate_{index}"]
                        recommendations.append(
                            {
                                "model": candidate.model_name,
                                "field": candidate.field_name,
                                "index_recommendation": _map_index_recommendation(answer.choice),
                                "confidence": answer.confidence,
                                "probabilities": answer.probabilities,
                            }
                        )
        except httpx.HTTPStatusError as exc:
            logger.warning("Jev request failed with HTTP %s", exc.response.status_code)
            if exc.response.status_code == 401:
                message = (
                    "TypeSafe rejected the API key (HTTP 401). Use the active key shown in "
                    "the TypeSafe API Keys page."
                )
            elif exc.response.status_code == 403:
                message = (
                    "Jev denied this request (HTTP 403). Check account access and model "
                    "availability."
                )
            elif exc.response.status_code == 404:
                message = "Jev endpoint was not found (HTTP 404). Check JEV_URL."
            elif exc.response.status_code == 422:
                message = (
                    "Jev rejected the request (HTTP 422). Check JEV_MODEL and the request contract."
                )
            else:
                message = f"Jev returned HTTP {exc.response.status_code}. Check Jev configuration."
            raise SpecAdvisorUnavailableError(message) from exc
        except httpx.TimeoutException as exc:
            logger.warning("Jev request timed out")
            raise SpecAdvisorUnavailableError("Jev request timed out.") from exc
        except httpx.RequestError as exc:
            logger.warning("Could not connect to Jev: %s", type(exc).__name__)
            raise SpecAdvisorUnavailableError(
                "Could not connect to Jev. Check JEV_URL and network connectivity."
            ) from exc
        except (ValueError, ValidationError) as exc:
            logger.warning("Jev returned an invalid response: %s", type(exc).__name__)
            raise SpecAdvisorUnavailableError(
                "Jev returned an invalid response. Check the Jev response schema and model."
            ) from exc

        return {
            "provider": "jev-ai",
            "model": JEV_MODEL,
            "recommendations": recommendations,
        }


def _index_candidates(spec: SpecV1) -> Iterator[JevIndexCandidate]:
    for model in spec.models:
        for field in model.fields:
            # Existing indexes, unique constraints and primary keys already cover
            # this decision, so asking Jev again would produce redundant advice.
            if field.index or field.unique or field.primary_key:
                continue
            endpoint_filters = _endpoint_filter_usage(spec, model, field.name)
            named_queries = _named_query_usage(model, field.name)
            relation_usage = _relation_usage(spec, model, field.name)
            used_in_filters = bool(endpoint_filters or named_queries)
            used_in_relations = bool(relation_usage)
            if not (used_in_filters or used_in_relations):
                continue
            yield JevIndexCandidate(
                model_name=model.name,
                field_name=field.name,
                field_type=field.type.value,
                already_indexed=False,
                used_in_filters=used_in_filters,
                used_in_relations=used_in_relations,
                query_operations=sorted(
                    {
                        query_filter.op.value
                        for endpoint in spec.api.endpoints
                        if endpoint.model == model.name
                        for query_filter in endpoint.filters
                        if query_filter.field == field.name
                    }
                    | {
                        query_filter.op.value
                        for query in model.queries
                        for query_filter in query.params
                        if query_filter.field == field.name
                    }
                ),
                endpoint_filters=endpoint_filters,
                named_queries=named_queries,
                relation_usage=relation_usage,
            )


def _endpoint_filter_usage(spec: SpecV1, model: ModelSpec, field_name: str) -> list[str]:
    return sorted(
        {
            f"{endpoint.method.value} {endpoint.path} ({query_filter.op.value})"
            for endpoint in spec.api.endpoints
            if endpoint.model == model.name
            for query_filter in endpoint.filters
            if query_filter.field == field_name
        }
    )


def _named_query_usage(model: ModelSpec, field_name: str) -> list[str]:
    return sorted(
        {
            f"{query.name} ({query_filter.op.value})"
            for query in model.queries
            for query_filter in query.params
            if query_filter.field == field_name
        }
    )


def _relation_usage(spec: SpecV1, model: ModelSpec, field_name: str) -> list[str]:
    local_relations = [
        f"{model.name}.{relation.name} ({relation.relation_type.value}, local field)"
        for relation in model.relations
        if relation.local_field == field_name
    ]
    target_relations = [
        f"{other_model.name}.{relation.name} ({relation.relation_type.value}, target field)"
        for other_model in spec.models
        for relation in other_model.relations
        if relation.target == model.name and relation.target_field == field_name
    ]
    return sorted(set(local_relations + target_relations))


def _batches(items: list[JevIndexCandidate]) -> Iterator[list[JevIndexCandidate]]:
    for start in range(0, len(items), MAX_QUESTIONS_PER_REQUEST):
        yield items[start : start + MAX_QUESTIONS_PER_REQUEST]


def _request_for_batch(candidates: list[JevIndexCandidate], *, model: str) -> JevRequest:
    questions = {
        f"candidate_{index}": JevChoiceQuestion(
            instructions=(
                f"Should {candidate.model_name}.{candidate.field_name} have a database index? "
                "Weigh exact lookups and range predicates against substring/pattern searches, "
                "which may need specialized indexes or may not benefit from a standard index. "
                "Only recommend an index when the supplied usage supports it; otherwise choose "
                "unnecessary or human_review."
            ),
            criteria=_CRITERIA,
        )
        for index, candidate in enumerate(candidates)
    }
    return JevRequest(
        model=model,
        state=JevIndexState(candidates=candidates),
        questions=questions,
    )


def _is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _map_index_recommendation(choice: str) -> str:
    """Translate provider-specific choice labels into the API's index decision."""
    return {
        "recommended": "recommended",
        "unnecessary": "not_recommended",
        "human_review": "review",
    }[choice]
