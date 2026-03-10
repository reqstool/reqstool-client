# Copyright © LFV

from pydantic import BaseModel, Field

from reqstool_python_decorators.decorators.decorators import Requirements


class RequirementsIndataPathItem(BaseModel):
    path: str
    exists: bool = False


@Requirements("REQ_016")
class RequirementsIndataPaths(BaseModel):
    # static
    requirements_yml: RequirementsIndataPathItem = Field(
        default_factory=lambda: RequirementsIndataPathItem(path="requirements.yml")
    )

    svcs_yml: RequirementsIndataPathItem = Field(
        default_factory=lambda: RequirementsIndataPathItem(path="software_verification_cases.yml")
    )
    mvrs_yml: RequirementsIndataPathItem = Field(
        default_factory=lambda: RequirementsIndataPathItem(path="manual_verification_results.yml")
    )

    # generated
    annotations_yml: RequirementsIndataPathItem = Field(
        default_factory=lambda: RequirementsIndataPathItem(path="annotations.yml")
    )
