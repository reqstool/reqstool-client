# Copyright © LFV

from typing import List, Optional

from pydantic import BaseModel, Field


class Resources(BaseModel):
    requirements: Optional[str] = None
    software_verification_cases: Optional[str] = None
    manual_verification_results: Optional[str] = None
    annotations: Optional[str] = None
    test_results: Optional[List[str]] = None


class ReqstoolConfig(BaseModel):
    language: Optional[str] = None
    build: Optional[str] = None
    resources: Optional[Resources] = Field(default_factory=Resources)

    @staticmethod
    def _parse(yaml_data: dict) -> "ReqstoolConfig":
        if not yaml_data:
            return ReqstoolConfig()

        r_language = yaml_data.get("language", None)
        r_build = yaml_data.get("build", None)

        # Parse resources
        resources_data = yaml_data.get("resources", None)

        if not resources_data:
            r_resources = Resources()
        else:
            r_resources = Resources(
                requirements=(resources_data["requirements"] if "requirements" in resources_data else None),
                software_verification_cases=(
                    resources_data["software_verification_cases"]
                    if "software_verification_cases" in resources_data
                    else None
                ),
                manual_verification_results=(
                    resources_data["manual_verification_results"]
                    if "manual_verification_results" in resources_data
                    else None
                ),
                annotations=resources_data["annotations"] if "annotations" in resources_data else None,
                test_results=resources_data["test_results"] if "test_results" in resources_data else None,
            )

        return ReqstoolConfig(
            language=r_language,
            build=r_build,
            resources=r_resources,
        )
