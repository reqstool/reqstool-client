# Copyright © LFV

import re
import sys
from enum import Enum, unique
from typing import Dict, List, Optional, Set

from reqstool_python_decorators.decorators.decorators import Requirements
from ruamel.yaml import YAML

from reqstool.commands.exit_codes import EXIT_CODE_SYNTAX_VALIDATION_ERROR
from reqstool.common.dataclasses.lifecycle import LifecycleData
from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.utils import Utils
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.common.validators.syntax_validator import JsonSchemaTypes, SyntaxValidator
from reqstool.filters.requirements_filters import RequirementFilter
from reqstool.locations.git_location import GitLocation
from reqstool.locations.local_location import LocalLocation
from reqstool.locations.location import LOCATIONTYPES, LocationInterface
from reqstool.locations.maven_location import MavenLocation
from reqstool.locations.pypi_location import PypiLocation
from reqstool.models.implementations import (
    GitImplData,
    ImplementationDataInterface,
    LocalImplData,
    MavenImplData,
    PypiImplData,
)
from reqstool.models.imports import GitImportData, ImportDataInterface, LocalImportData, MavenImportData, PypiImportData
from reqstool.models.requirements import (
    CATEGORIES,
    IMPLEMENTATION,
    SIGNIFICANCETYPES,
    VARIANTS,
    MetaData,
    ReferenceData,
    RequirementData,
    RequirementsData,
)


@unique
class LOCATION_SOURCE_TYPES(Enum):
    implementations = "implementations"
    imports = "imports"


class RequirementsModelGenerator:

    def __init__(
        self,
        parent: LocationInterface,
        semantic_validator: SemanticValidator,
        filename: str,
        prefix_with_urn: bool = False,
    ):
        self.parent = parent
        self.filename = filename
        self.prefix_with_urn = prefix_with_urn
        self.semantic_validator = semantic_validator
        self.requirements_data = self.__generate(filename)

    @staticmethod
    def get_urn_if_available(data: str) -> str:
        # Regular expression pattern to match the URN value
        pattern = r"urn:\s*([^\n]+)"

        # Search for the pattern in the text
        match = re.search(pattern, data)

        # Extract URN value if found, otherwise set to "unknown"
        urn = match.group(1) if match else "unknown"

        return urn

    def __generate(
        self,
        uri: str,
    ) -> RequirementsData:
        response = Utils.open_file_https_file(uri)

        yaml = YAML(typ="safe")

        data = yaml.load(response.text)

        urn = self.get_urn_if_available(response.text)

        if not SyntaxValidator.is_valid_data(json_schema_type=JsonSchemaTypes.REQUIREMENTS, data=data, urn=urn):
            sys.exit(EXIT_CODE_SYNTAX_VALIDATION_ERROR)

        r_metadata: MetaData = self.__parse_metadata(data["metadata"])

        r_implementations: List[ImplementationDataInterface] = []
        r_imports: List[ImportDataInterface] = []
        r_requirements: Dict[str, RequirementData] = {}
        r_filters: Dict[str, RequirementFilter] = {}

        match r_metadata.variant:
            case VARIANTS.SYSTEM:
                self.prefix_with_urn = False
                r_imports = self.__parse_imports(data=data)
                r_filters = self.__parse_requirement_filters(data=data)
                r_implementations = self.__parse_implementations(data=data)
                r_requirements = self.__parse_requirements(data=data)
            case VARIANTS.MICROSERVICE:
                self.prefix_with_urn = False
                r_imports = self.__parse_imports(data=data)
                r_filters = self.__parse_requirement_filters(data=data)
                r_requirements = self.__parse_requirements(data=data)
            case VARIANTS.EXTERNAL:
                self.prefix_with_urn = False
                r_requirements = self.__parse_requirements(data=data)
            case _:
                raise RuntimeError("Unsupported system type")

        return RequirementsData(
            metadata=r_metadata,
            implementations=r_implementations,
            imports=r_imports,
            requirements=r_requirements,
            filters=r_filters,
        )

    def __parse_metadata(self, data):
        r_urn: str = data["urn"]
        r_variant: VARIANTS = VARIANTS(data["variant"])
        r_title: str = data["title"]
        r_url: str = None if "url" not in data else data["url"]

        return MetaData(urn=r_urn, variant=r_variant, title=r_title, url=r_url)

    def __parse_implementations(self, data):
        locations = []

        if LOCATION_SOURCE_TYPES.implementations.value in data:
            # local
            self.__parse_location_local(
                location_source_types=LOCATION_SOURCE_TYPES.implementations,
                data=data,
                instance_type=LocalImplData,
                locations=locations,
            )

            # git
            self.__parse_location_git(
                location_source_types=LOCATION_SOURCE_TYPES.implementations,
                data=data,
                instance_type=GitImplData,
                locations=locations,
            )

            # maven
            self.__parse_location_maven(
                location_source_types=LOCATION_SOURCE_TYPES.implementations,
                data=data,
                instance_type=MavenImplData,
                locations=locations,
            )
            # pypi
            self.__parse_location_pypi(
                location_source_types=LOCATION_SOURCE_TYPES.implementations,
                data=data,
                instance_type=PypiImplData,
                locations=locations,
            )

        return locations

    def __parse_imports(self, data):
        locations = []

        if LOCATION_SOURCE_TYPES.imports.value in data:
            # local
            self.__parse_location_local(
                location_source_types=LOCATION_SOURCE_TYPES.imports,
                data=data,
                instance_type=LocalImportData,
                locations=locations,
            )

            # git
            self.__parse_location_git(
                location_source_types=LOCATION_SOURCE_TYPES.imports,
                data=data,
                instance_type=GitImportData,
                locations=locations,
            )

            # maven
            self.__parse_location_maven(
                location_source_types=LOCATION_SOURCE_TYPES.imports,
                data=data,
                instance_type=MavenImportData,
                locations=locations,
            )
            # pypi
            self.__parse_location_pypi(
                location_source_types=LOCATION_SOURCE_TYPES.imports,
                data=data,
                instance_type=PypiImportData,
                locations=locations,
            )

        return locations

    def __parse_location_maven(self, location_source_types: LOCATION_SOURCE_TYPES, data, instance_type, locations):
        if LOCATIONTYPES.MAVEN.value in data[location_source_types.value]:
            for maven in data[location_source_types.value][LOCATIONTYPES.MAVEN.value]:
                MAVEN_CENTRAL_REPO_URL: str = "https://repo.maven.apache.org/maven2/"

                maven_location = instance_type(
                    parent=self.parent,
                    _current_unresolved=MavenLocation(
                        env_token=maven["env_token"] if "env_token" in maven else None,
                        url=maven["url"] if "url" in maven else MAVEN_CENTRAL_REPO_URL,
                        group_id=maven["group_id"],
                        artifact_id=maven["artifact_id"],
                        version=maven["version"],
                        classifier=maven["classifier"] if "classifier" in maven else "reqstool",
                    ),
                )

                locations.append(maven_location)

    def __parse_location_pypi(self, location_source_types: LOCATION_SOURCE_TYPES, data, instance_type, locations):
        if LOCATIONTYPES.PYPI.value in data[location_source_types.value]:
            for pypi in data[location_source_types.value][LOCATIONTYPES.PYPI.value]:
                PYPI_ORG_SIMPLE_API_URL: str = "https://pypi.org/simple/"

                pypi_location = instance_type(
                    parent=self.parent,
                    _current_unresolved=PypiLocation(
                        env_token=pypi["env_token"] if "env_token" in pypi else None,
                        url=pypi["url"] if "url" in pypi else PYPI_ORG_SIMPLE_API_URL,
                        package=pypi["package"],
                        version=pypi["version"],
                    ),
                )

                locations.append(pypi_location)

    def __parse_location_local(self, location_source_types: LOCATION_SOURCE_TYPES, data, instance_type, locations):
        if LOCATIONTYPES.LOCAL.value in data[location_source_types.value]:
            for local in data[location_source_types.value][LOCATIONTYPES.LOCAL.value]:
                local_location = instance_type(
                    parent=self.parent, _current_unresolved=LocalLocation(path=local["path"])
                )

                locations.append(local_location)

    def __parse_location_git(self, location_source_types: LOCATION_SOURCE_TYPES, data, instance_type, locations):
        if LOCATIONTYPES.GIT.value in data[location_source_types.value]:
            for git in data[location_source_types.value][LOCATIONTYPES.GIT.value]:
                git_location = instance_type(
                    parent=self.parent,
                    _current_unresolved=GitLocation(
                        env_token=git["env_token"] if "env_token" in git else None,
                        url=git["url"],
                        branch=git["branch"],
                        path=git["path"],
                    ),
                )

                locations.append(git_location)

    def __parse_requirement_filters(self, data) -> Dict[str, RequirementFilter]:  # NOSONAR
        r_filters = {}

        self.semantic_validator._validate_req_imports_filter_has_excludes_xor_includes(data)

        if "filters" in data:
            for urn in data["filters"].keys():
                urn_filter = data["filters"][urn]

                req_urn_ids_imports: Optional[Set[UrnId]] = None
                req_urn_ids_excludes: Optional[Set[UrnId]] = None
                custom_includes = None
                custom_exclude = None

                if "requirement_ids" in urn_filter:
                    if "includes" in urn_filter["requirement_ids"]:
                        filtered_ids = Utils.check_ids_to_filter(
                            current_urn=urn, ids=urn_filter["requirement_ids"]["includes"]
                        )
                        req_ids_includes = set(filtered_ids)
                        req_urn_ids_imports: Set[UrnId] = set(
                            Utils.convert_ids_to_urn_id(urn=urn, ids=req_ids_includes)
                        )

                    if "excludes" in urn_filter["requirement_ids"]:
                        filtered_ids = Utils.check_ids_to_filter(
                            current_urn=urn, ids=urn_filter["requirement_ids"]["excludes"]
                        )
                        req_ids_excludes = set(filtered_ids)
                        req_urn_ids_excludes: Set[UrnId] = set(
                            Utils.convert_ids_to_urn_id(urn=urn, ids=req_ids_excludes)
                        )

                if "custom" in urn_filter:
                    if "includes" in urn_filter["custom"]:
                        custom_includes = urn_filter["custom"]["includes"]

                    if "excludes" in urn_filter["custom"]:
                        custom_exclude = urn_filter["custom"]["excludes"]

                req_filter = RequirementFilter(
                    urn_ids_imports=req_urn_ids_imports,
                    urn_ids_excludes=req_urn_ids_excludes,
                    custom_imports=custom_includes,
                    custom_exclude=custom_exclude,
                )

                r_filters[urn] = req_filter

        return r_filters

    @Requirements("REQ_004", "REQ_036")
    def __parse_requirements(self, data):  # NOSONAR
        r_reqs = {}

        self.semantic_validator._validate_no_duplicate_requirement_ids(data=data)

        if "requirements" in data:
            for req in data["requirements"]:
                refs_data = []
                urn = data["metadata"]["urn"]

                if "references" in req:
                    refs_data.extend(
                        [
                            ReferenceData(
                                requirement_ids=Utils.convert_ids_to_urn_id(
                                    ids=req["references"]["requirement_ids"], urn=urn
                                )
                            )
                        ]
                    )

                rationale = req.get("rationale")
                implementation = req.get("implementation", IMPLEMENTATION.IN_CODE.value)
                urn_id = UrnId(urn=urn, id=req["id"])
                req_data = RequirementData(
                    id=urn_id,
                    title=req["title"],
                    significance=SIGNIFICANCETYPES(req["significance"]),
                    description=req["description"],
                    rationale=rationale,
                    implementation=IMPLEMENTATION(implementation),
                    categories=[CATEGORIES(c) for c in req["categories"]],
                    references=refs_data,
                    revision=Utils.parse_version(version_str=req["revision"], urn_id=urn_id),
                    lifecycle=LifecycleData.from_dict(req.get("lifecycle")),
                )

                if req_data.id not in r_reqs:
                    r_reqs[req_data.id] = req_data

        return r_reqs
