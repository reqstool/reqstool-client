# Copyright © LFV

import os
import sys
from pathlib import Path
from typing import List, Union

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from reqstool_python_decorators.decorators.decorators import Requirements
from ruamel.yaml import YAML

from reqstool.commands.exit_codes import EXIT_CODE_SYNTAX_VALIDATION_ERROR
from reqstool.common.utils import Utils
from reqstool.common.validators.syntax_validator import JsonSchemaTypes, SyntaxValidator
from reqstool.locations.git_location import GitLocation
from reqstool.locations.local_location import LocalLocation
from reqstool.locations.local_maven_location import LocalMavenLocation
from reqstool.locations.local_pypi_location import LocalPypiLocation
from reqstool.locations.location import LocationInterface
from reqstool.locations.maven_location import MavenLocation
from reqstool.locations.pypi_location import PypiLocation
from reqstool.reqstool_config.reqstool_config import ReqstoolConfig
from reqstool.requirements_indata.requirements_indata_paths import RequirementsIndataPathItem, RequirementsIndataPaths


class RequirementsIndata(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    dst_path: Union[str, Path]  # tmp path
    location: LocationInterface  # current location
    reqstool_config: ReqstoolConfig = Field(init=False, default=None)
    requirements_indata_paths: RequirementsIndataPaths = Field(default_factory=RequirementsIndataPaths)
    test_results_patterns: List[str] = Field(default_factory=list)

    def model_post_init(self, __context):
        self._handle_requirements_config()
        self._ensure_absolute_paths_and_check_existance()

    @Requirements("REQ_011")
    def _handle_requirements_config(self):

        if os.path.exists(os.path.join(self.dst_path, "reqstool_config.yml")):
            response = Utils.open_file_https_file(os.path.join(self.dst_path, "reqstool_config.yml"))

            yaml = YAML(typ="safe")

            data: dict = yaml.load(response.text)

            if not SyntaxValidator.is_valid_data(
                json_schema_type=JsonSchemaTypes.REQSTOOL_CONFIG, data=data, urn="unknown"
            ):
                sys.exit(EXIT_CODE_SYNTAX_VALIDATION_ERROR)

            self.reqstool_config = ReqstoolConfig._parse(yaml_data=data)

            self._update_with_reqstool_config_values()

    def _ensure_absolute_paths_and_check_existance(self):
        # iterate over all fields and ensure absolute paths

        for field_name in RequirementsIndataPaths.model_fields:
            original: Union[RequirementsIndataPathItem, List[RequirementsIndataPathItem]] = getattr(
                self.requirements_indata_paths, field_name
            )

            if isinstance(self.location, GitLocation):
                # Include self.location.path when resolving a git repository
                RequirementsIndata._ensure_absolute_path_and_check_existance(
                    paths=[self.dst_path, self.location.path], original=original
                )
            elif isinstance(self.location, (MavenLocation, LocalMavenLocation, PypiLocation, LocalPypiLocation)):
                RequirementsIndata._ensure_absolute_path_and_check_existance(paths=[self.dst_path], original=original)
            elif isinstance(self.location, LocalLocation):
                # resolve soft link
                abs_dst_path = os.readlink(self.dst_path)
                RequirementsIndata._ensure_absolute_path_and_check_existance(paths=[abs_dst_path], original=original)
            else:
                raise TypeError(f"Unknown location type: {type(self.location)}")

    def _ensure_absolute_path_and_check_existance(
        paths: List[str], original: Union[RequirementsIndataPathItem, List[RequirementsIndataPathItem]]
    ):

        new_abs_path = os.path.abspath(os.path.join(*paths, original.path))
        original.path = new_abs_path
        original.exists = os.path.exists(original.path)

    def _update_with_reqstool_config_values(self):
        # replace default values with those specified in reqstool_config.yml

        if self.reqstool_config.resources.requirements:
            self.requirements_indata_paths.requirements_yml = RequirementsIndataPathItem(
                path=self.reqstool_config.resources.requirements
            )

        if self.reqstool_config.resources.software_verification_cases:
            self.requirements_indata_paths.svcs_yml = RequirementsIndataPathItem(
                path=self.reqstool_config.resources.software_verification_cases
            )

        if self.reqstool_config.resources.manual_verification_results:
            self.requirements_indata_paths.mvrs_yml = RequirementsIndataPathItem(
                path=self.reqstool_config.resources.manual_verification_results
            )

        if self.reqstool_config.resources.test_results:
            self.test_results_patterns.extend(self.reqstool_config.resources.test_results)

        if self.reqstool_config.resources.annotations:
            self.requirements_indata_paths.annotations_yml = RequirementsIndataPathItem(
                path=self.reqstool_config.resources.annotations
            )
