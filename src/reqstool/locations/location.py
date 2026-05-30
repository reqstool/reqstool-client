# Copyright © LFV

import re
from abc import ABC, abstractmethod
from enum import Enum, unique

from pydantic import BaseModel, ConfigDict

_SUFFIX_MAX_LEN = 80
_UNSAFE_PATH_CHARS = re.compile(r"[^a-zA-Z0-9._-]")


@unique
class LOCATIONTYPES(Enum):
    GIT = "git"
    LOCAL = "local"
    MAVEN = "maven"
    NPM = "npm"
    PYPI = "pypi"


def make_safe_tmpdir_suffix(prefix: str, uri: str) -> str:
    """Return a filesystem-safe temp-dir suffix: '{prefix}_{sanitized_uri}' capped at _SUFFIX_MAX_LEN chars."""
    sanitized = re.sub(r"\.{2,}", "_", _UNSAFE_PATH_CHARS.sub("_", uri))
    return f"{prefix}_{sanitized}"[:_SUFFIX_MAX_LEN]


class LocationInterface(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @abstractmethod
    def _make_available_on_localdisk(self, dst_path: str) -> str:
        pass

    @abstractmethod
    def tmpdir_key(self) -> str:
        """Return a short, filesystem-safe string identifying this location for use as a temp-dir suffix."""
