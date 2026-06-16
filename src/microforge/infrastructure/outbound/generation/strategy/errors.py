class UnsupportedTargetError(Exception):
    """Raised when an unsupported target is specified."""
    def __init__(self, language: str, framework: str):
        super().__init__(f"Unsupported target: language={language}, framework={framework}")