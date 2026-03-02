# Copyright © LFV


class MissingRequirementsFileError(Exception):
    """Raised when a required requirements.yml file cannot be found at the resolved path."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Missing requirements file: {path}")
