# Copyright © LFV

from pathlib import PurePath
from typing import Optional

from pydantic import BaseModel, ConfigDict

from reqstool.locations.local_location import LocalLocation
from reqstool.locations.location import LocationInterface


class LocationResolver(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    current_unresolved: LocationInterface
    parent: Optional[LocationInterface] = None
    current: Optional[LocationInterface] = None

    def model_post_init(self, __context):
        object.__setattr__(self, "current", self.__resolve_resolved())

    def __resolve_resolved(self) -> LocationInterface:
        # Parent: None   Current: X     -> Resolved: X
        if self.parent is None:
            resolved = self.current_unresolved
        elif isinstance(self.current_unresolved, LocalLocation):
            # Parent: X  Current: Local -> Resolved: X (resolve path)
            if PurePath(self.current_unresolved.path).is_absolute():
                new_path = self.current_unresolved.path
            else:
                new_path = PurePath(self.parent.path, self.current_unresolved.path)

            resolved = self.parent.model_copy(update={"path": new_path})

        # Parent: Local  Current: Git   -> Resolved: Git
        # Parent: Local  Current: Maven -> Resolved: Maven
        # Parent: Local  Current: Pypi  -> Resolved: Pypi
        # Parent: Git    Current: Git   -> Resolved: Git
        # Parent: Git    Current: Maven -> Resolved: Maven
        # Parent: Maven  Current: Git   -> Resolved: Git
        # Parent: Maven  Current: Maven -> Resolved: Maven
        # etc
        else:
            resolved = self.current_unresolved

        return resolved

    def make_available_on_localdisk(self, dst_path: str) -> str:
        return self.current._make_available_on_localdisk(dst_path=dst_path)
