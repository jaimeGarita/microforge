# AI Advisor

This document defines the proposed use of decision-oriented AI in Microforge.
It is a design proposal, not an implemented feature.

## Purpose

Microforge should use AI to make bounded recommendations where several reasonable
options exist. AI must not replace deterministic validation, code generation, or
security rules.

The first proposed capability is an **AI Architecture Advisor**. It analyzes a valid
Microforge specification and returns optional, typed recommendations that the user can
accept or reject.

```text
Specification
      |
      +--> deterministic validation --> validation errors
      |
      +--> AI advisor -------------> optional recommendations
                                           |
                                      accept / reject
```

## Core decisions

- The existing deterministic generator remains the source of truth.
- A specification must pass structural and semantic validation before AI analysis.
- AI recommendations never mutate a specification automatically.
- Every recommendation has a predefined type, target, decision, and confidence.
- Low-confidence decisions are shown for human review instead of being applied.
- AI availability must not block validation or project generation.
- Provider-specific concepts and credentials stay in infrastructure.
- The first provider considered is TypeSafe Jev, hidden behind an application port.
- The integration starts with architecture advice, not code or prose generation.

## Appropriate AI decisions

Initial candidates:

- Whether a collection endpoint should use pagination.
- Whether a field is a good candidate for a database index.
- Whether a model is a good candidate for soft deletion.
- Whether an operation likely needs an explicit transaction.
- Whether a field appears to contain sensitive information.
- Which identifier strategy best fits a model.
- Which testing profile fits a generated service.
- Whether a specification should receive human architecture review.

These decisions are recommendations because their correct answer depends on expected
usage, scale, and business context that cannot always be expressed as a fixed rule.

## Decisions that remain deterministic

AI must not decide:

- Whether referenced models or fields exist.
- Whether field types are compatible.
- Whether YAML or JSON is structurally valid.
- Whether an identifier is valid Python.
- Whether file paths or generated names collide.
- Whether a foreign key is structurally valid.
- Which imports are required by generated code.
- How templates are rendered.
- Whether generated Python compiles.

Rule of thumb:

```text
Exact answer                    -> normal code
Bounded, contextual judgment    -> decision model
Text or code creation           -> generative model
```

## Proposed API

### Analyze a specification

```http
POST /api/v1/spec/advise
Content-Type: multipart/form-data
```

The request uses the same `file` field as the validation and generation endpoints.

Example response:

```json
{
  "specHash": "abc123",
  "recommendations": [
    {
      "code": "database_index",
      "target": "Order.customer_id",
      "decision": "recommended",
      "confidence": 0.91,
      "status": "suggestion"
    },
    {
      "code": "pagination",
      "target": "endpoint:listOrders",
      "decision": "required",
      "confidence": 0.95,
      "status": "suggestion"
    }
  ]
}
```

### Apply accepted recommendations

This endpoint is a later phase:

```http
POST /api/v1/spec/recommendations/apply
Content-Type: application/json
```

Example request:

```json
{
  "specHash": "abc123",
  "accepted": [
    {
      "code": "database_index",
      "target": "Order.customer_id"
    }
  ]
}
```

It should return a new proposed specification and never overwrite the original input.
The hash prevents applying recommendations to a specification that has changed since
it was analyzed.

## Domain model

Possible initial types:

```python
class RecommendationType(str, Enum):
    pagination = "pagination"
    database_index = "databaseIndex"
    soft_delete = "softDelete"
    transaction = "transaction"


class RecommendationStatus(str, Enum):
    suggestion = "suggestion"
    uncertain = "uncertain"
    human_review = "humanReview"


class SpecRecommendation(SpecModel):
    code: RecommendationType
    target: str
    decision: str
    confidence: float
    status: RecommendationStatus
```

The final model should avoid a completely free-form `decision` if each recommendation
can expose its own enum or constrained value type.

## Proposed architecture

```text
src/microforge/
├── domain/
│   └── advisory/
│       ├── models.py
│       └── policies.py
├── application/
│   └── advisory/
│       ├── ports/
│       │   ├── inbound.py
│       │   └── outbound.py
│       └── use_cases/
│           └── advise_spec.py
└── infrastructure/
    └── outbound/
        └── intelligence/
            └── jev_spec_advisor.py
```

### Outbound port

```python
class SpecAdvisorPort(Protocol):
    def advise(self, spec: SpecV1) -> list[SpecRecommendation]:
        ...
```

The application depends on this contract, not on Jev or its HTTP API.

### Use case

```python
class AdviseSpecUseCase:
    def __init__(
        self,
        loader: SpecLoaderPort,
        advisor: SpecAdvisorPort,
    ):
        self.loader = loader
        self.advisor = advisor

    def run_bytes(self, data: bytes) -> list[SpecRecommendation]:
        spec = self.loader.load_bytes(data)
        validate_semantics(spec)
        return self.advisor.advise(spec)
```

### Jev adapter

The adapter is responsible for:

- Building a minimal state from `SpecV1`.
- Defining bounded questions and accepted answers.
- Calling the provider API.
- Mapping provider responses to domain recommendations.
- Enforcing timeouts and limited retries.
- Rejecting malformed or incomplete provider responses.
- Recording latency, model version, and usage metadata.

It must not place API keys, provider response objects, or HTTP details in the domain.

## Input minimization

The advisor should send only the context needed for each decision. It should not send
the complete uploaded source when a smaller structured state is sufficient.

Example index recommendation state:

```json
{
  "model": "Order",
  "field": {
    "name": "customer_id",
    "type": "uuid",
    "index": false,
    "usedByRelation": true,
    "usedByFilters": true
  },
  "collectionEndpoints": 1
}
```

Benefits:

- Lower latency and cost.
- Less sensitive information sent externally.
- More focused and testable decisions.
- Easier provider replacement.

## Confidence policy

Initial illustrative thresholds:

```text
confidence >= 0.90  -> suggestion
confidence >= 0.65  -> uncertain
confidence < 0.65   -> human review
```

These values must be configuration, not hard-coded business truth. They should be
calibrated using a labeled evaluation dataset before enabling automatic application.

Typed output prevents out-of-schema answers, but it does not guarantee that the chosen
answer is correct.

## Failure behavior

If the provider is unavailable, times out, or returns an invalid response:

- Validation continues to work.
- Project generation continues to work.
- The advice endpoint returns a controlled availability error.
- Provider internals and credentials are never exposed.
- The system does not silently replace missing advice with invented recommendations.

Suggested error shape:

```json
{
  "detail": {
    "code": "advisor_unavailable",
    "message": "Architecture advice is temporarily unavailable."
  }
}
```

## Security and privacy

- Read the API key exclusively from `TYPESAFE_API_KEY` or equivalent secret storage.
- Never place the API key in the generated project or frontend bundle.
- Document that selected specification metadata is sent to an external provider.
- Avoid sending descriptions or defaults that may contain secrets unless required.
- Redact suspicious values before building provider state.
- Define connection and response-size limits.
- Log metadata, not full specifications or provider payloads.
- Make external advice explicitly opt-in.

## Evaluation

Before trusting recommendations, create a small labeled dataset:

```text
test/advisory/cases/
├── pagination.yaml
├── indexes.yaml
└── soft_delete.yaml
```

Each case should contain:

- A Microforge specification.
- The expected bounded decision.
- Decisions that should be considered acceptable.
- A short human rationale kept only for evaluation.

Measure:

- Accuracy by recommendation type.
- Confidence calibration.
- False-positive rate.
- Latency.
- Provider errors and timeouts.
- User acceptance and rejection rate.

Provider-backed tests should not run in the normal unit test suite. Unit tests use a
fake `SpecAdvisorPort`; optional integration tests use a real API key.

## Implementation phases

### Phase 1: provider-independent foundation

- [ ] Define recommendation domain types.
- [ ] Define `SpecAdvisorPort`.
- [ ] Implement `AdviseSpecUseCase`.
- [ ] Implement a deterministic fake advisor.
- [ ] Add unit tests without network access.

### Phase 2: first useful recommendations

- [ ] Add pagination decisions.
- [ ] Add database-index decisions.
- [ ] Add soft-delete decisions.
- [ ] Add `POST /api/v1/spec/advise`.
- [ ] Return a hash of the analyzed specification.

### Phase 3: Jev adapter

- [ ] Add configuration and secret handling.
- [ ] Implement the TypeSafe API client.
- [ ] Map Microforge state to bounded questions.
- [ ] Add timeout, retry, and response validation.
- [ ] Record provider and model metadata.
- [ ] Add opt-in integration tests.

### Phase 4: product feedback loop

- [ ] Display recommendations in the frontend.
- [ ] Allow explicit acceptance and rejection.
- [ ] Store anonymous decision-quality metrics if the user opts in.
- [ ] Build and maintain the evaluation dataset.
- [ ] Calibrate confidence thresholds.

### Phase 5: safe application

- [ ] Add a recommendation-application service.
- [ ] Return a new proposed specification.
- [ ] Show a diff before acceptance.
- [ ] Never overwrite user input automatically.

## Future direction: intelligence in generated projects

A later version of the Microforge format could declare bounded business decisions:

```yaml
intelligence:
  provider: jev
  decisions:
    - name: classifyOrderRisk
      state:
        model: Order
        fields:
          - total_amount
          - status
          - customer_country
      output:
        type: choice
        choices:
          normal: Process normally
          review: Require manual review
          blocked: Block the order
```

Microforge could generate an application port, use case, provider adapter, configuration,
and tests for that decision. This is deliberately outside the first advisor MVP.

## Open questions

- Should advice be available only through the API or also through a future CLI?
- Which three recommendations provide enough value for the first experiment?
- Should the API return provider metadata to clients or keep it internal?
- How should recommendation-specific decisions be modeled without free-form strings?
- Which specification fields are safe and necessary to send externally?
- Should accepted recommendations become an auditable decision record?
- What confidence threshold is appropriate for each recommendation type?
- Is provider fallback desirable, or should advice fail explicitly?

These questions should be resolved with small experiments and evaluation data rather
than by making the AI integration broader from the beginning.
