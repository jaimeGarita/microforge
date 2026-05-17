from enum import Enum


class TargetLanguage(str, Enum):
    """Supported programming languages."""

    python = "python"


class TargetFramework(str, Enum):
    """Supported web frameworks."""

    fastapi = "fastapi"


class Packaging(str, Enum):
    """Supported packaging methods."""

    poetry = "poetry"
    pip = "pip"


class FieldType(str, Enum):
    """Field data types."""

    string = "string"
    int = "int"
    long = "long"
    boolean = "boolean"
    uuid = "uuid"
    decimal = "decimal"
    instant = "instant"
    date = "date"


class QueryOp(str, Enum):
    """Operations allowed in query filters."""

    eq = "eq"
    lt = "lt"
    lte = "lte"
    gt = "gt"
    gte = "gte"
    like = "like"
    in_ = "in"


class ApiHttpMethod(str, Enum):
    """Supported HTTP verbs."""

    get = "GET"
    post = "POST"
    put = "PUT"
    patch = "PATCH"
    delete = "DELETE"
