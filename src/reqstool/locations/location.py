# Copyright © LFV

from abc import ABC, abstractmethod
from enum import Enum, unique

from pydantic import BaseModel, ConfigDict


@unique
class LOCATIONTYPES(Enum):
    GIT = "git"
    LOCAL = "local"
    MAVEN = "maven"
    PYPI = "pypi"


class LocationInterface(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @abstractmethod
    def _make_available_on_localdisk(self, dst_path: str) -> str:
        pass
