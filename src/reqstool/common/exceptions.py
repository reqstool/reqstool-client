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


class ArtifactDownloadError(Exception):
    """Raised when a remote artifact cannot be downloaded."""

    def __init__(self, message: str):
        super().__init__(message)


class ArtifactExtractionError(Exception):
    """Raised when a downloaded artifact cannot be extracted."""

    def __init__(self, message: str):
        super().__init__(message)


class GitRefNotFoundError(Exception):
    """Raised when a git ref (branch, tag, or commit SHA) cannot be resolved in a cloned repo."""

    def __init__(self, ref: str, url: str):
        self.ref = ref
        self.url = url
        super().__init__(f"ref '{ref}' not found in {url}")


class EnvVarInterpolationError(Exception):
    """Raised when environment variable interpolation of YAML input fails.

    This covers references to unset variables that have no inline default, as
    well as malformed ``${...}`` expressions. Failing hard keeps ingestion
    deterministic and surfaces configuration mistakes in CI.
    """

    def __init__(self, message: str, source: str | None = None):
        self.source = source
        super().__init__(f"{message} (in {source})" if source else message)
