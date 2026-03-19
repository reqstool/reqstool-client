# Copyright © LFV


class MissingRequirementsFileError(Exception):
    """Raised when a required requirements.yml file cannot be found at the resolved path."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Missing requirements file: {path}")


class CircularImportError(Exception):
    """Raised when a circular import is detected in the requirements graph."""

    def __init__(self, urn: str, chain: list[str]):
        self.urn = urn
        super().__init__(f"Circular import detected: {' -> '.join(chain)} -> {urn}")


class CircularImplementationError(Exception):
    """Raised when a circular implementation chain is detected in the requirements graph."""

    def __init__(self, urn: str, chain: list[str]):
        self.urn = urn
        super().__init__(f"Circular implementation detected: {' -> '.join(chain)} -> {urn}")
