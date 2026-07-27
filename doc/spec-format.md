# Spec Format

This document describes the Microforge YAML spec fields currently supported by
the FastAPI generator.

## API Endpoints

Endpoints describe the HTTP surface generated for each model.

```yaml
api:
  basePath: /api/v1
  endpoints:
    - name: listCustomers
      model: Customer
      path: /customers
      method: GET
      filters:
        - field: email
          op: eq
        - field: created_at
          op: gte

    - name: createCustomer
      model: Customer
      path: /customers
      method: POST
```

### Endpoint Properties

| Property | Required | Description |
| --- | --- | --- |
| `name` | Yes | Logical endpoint name. Used to derive generated names. |
| `model` | Recommended | Model handled by the endpoint. Required when using `filters`. |
| `path` | Yes | Route path below `api.basePath`. |
| `method` | No | HTTP method. Defaults to `GET`. |
| `filters` | No | Query filters accepted by collection `GET` endpoints without path parameters. |

When `filters` are declared, Microforge generates:

- FastAPI query parameters.
- An application use case.
- A repository port method.
- A SQLAlchemy repository implementation.

For example:

```yaml
filters:
  - field: email
    op: eq
  - field: created_at
    op: gte
```

generates a repository method named:

```python
find_by_email_and_created_at_gte(...)
```

### Supported Filter Operators

| Operator | Meaning |
| --- | --- |
| `eq` | Equal |
| `ne` | Not equal |
| `lt` | Less than |
| `lte` | Less than or equal |
| `gt` | Greater than |
| `gte` | Greater than or equal |
| `like` | SQL LIKE |
| `not_like` | Negated SQL LIKE |
| `in` | SQL IN |
| `not_in` | Negated SQL IN |
| `contains` | SQL contains |
| `startswith` | Starts with |
| `endswith` | Ends with |

## Field Metadata

Each model field supports structural metadata:

```yaml
models:
  - name: Product
    fields:
      - name: id
        type: int
        primaryKey: true
      - name: sku
        type: string
        unique: true
        index: true
        minLength: 3
        maxLength: 30
      - name: status
        type: string
        enum: [draft, active]
        default: draft
      - name: price
        type: decimal
        minimum: 0
        default: "0.0"
      - name: description
        type: string
        nullable: true
```

### Supported Properties

| Property | Applies To | Generated Effect |
| --- | --- | --- |
| `primaryKey` | Any field | SQLAlchemy `primary_key=True` |
| `autoIncrement` | `int`, `long` | SQLAlchemy `autoincrement=True`; omitted from create payload |
| `nullable` | Non-primary-key fields | Python `T \| None`; SQLAlchemy `nullable=True` |
| `unique` | Any field | SQLAlchemy `unique=True` |
| `index` | Any field | SQLAlchemy `index=True` |
| `default` | Scalar fields | Pydantic `Field(default=...)`; SQLAlchemy `default=...` |
| `minLength` | `string` | Pydantic `Field(min_length=...)` |
| `maxLength` | `string` | Pydantic `Field(max_length=...)` |
| `minimum` | `int`, `long`, `decimal` | Pydantic `Field(ge=...)` |
| `maximum` | `int`, `long`, `decimal` | Pydantic `Field(le=...)` |
| `enum` | Scalar fields | Python `Literal[...]` in domain and schemas |

### Semantic Rules

Microforge validates model metadata before generation:

- `primaryKey: true` cannot be combined with `nullable: true`.
- `autoIncrement: true` requires `primaryKey: true`.
- `autoIncrement: true` is only supported for `int` and `long`.
- `minLength` and `maxLength` are only supported for `string`.
- `minimum` and `maximum` are only supported for `int`, `long`, and `decimal`.
- `minLength` cannot be greater than `maxLength`.
- `minimum` cannot be greater than `maximum`.
- `default` must match the field type.
- If `enum` is present, `default` must be one of the enum values.
- Endpoint `model` references must point to declared models.
- Endpoint `filters` require `model`.
- Endpoint `filters` must reference fields from the endpoint model.

## Generated Examples

This field:

```yaml
- name: sku
  type: string
  unique: true
  index: true
  minLength: 3
  maxLength: 30
```

generates a Pydantic schema field:

```python
sku: str = Field(min_length=3, max_length=30)
```

and a SQLAlchemy column:

```python
sku: Mapped[str] = mapped_column(unique=True, index=True)
```

This enum:

```yaml
- name: status
  type: string
  enum: [draft, active]
  default: draft
```

generates:

```python
status: Literal["draft", "active"] = Field(default="draft")
```

and:

```python
status: Mapped[Literal["draft", "active"]] = mapped_column(default="draft")
```
