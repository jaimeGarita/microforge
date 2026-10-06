"""Application errors raised while obtaining external spec recommendations."""


class SpecAdvisorUnavailableError(RuntimeError):
    """The configured recommendation provider could not return a valid answer."""
