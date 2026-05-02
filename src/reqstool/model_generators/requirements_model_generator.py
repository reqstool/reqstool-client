# Copyright © LFV

import re
import sys
from enum import Enum, unique
from typing import Dict, List

from reqstool_python_decorators.decorators.decorators import Requirements
from ruamel.yaml import YAML

from reqstool.commands.exit_codes import EXIT_CODE_SYNTAX_VALIDATION_ERROR
from reqstool.common.filter_parser import parse_filters
from reqstool.common.models.lifecycle import LifecycleData
from reqstool.common.models.urn_id import UrnId
from reqstool.common.utils import Utils
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.common.validators.syntax_validator import JsonSchemaTypes, SyntaxValidator
from reqstool.filters.requirements_filters import RequirementFilter
from reqstool.locations.git_location import GitLocation
from reqstool.locations.local_location import LocalLocation
from reqstool.locations.location import LocationInterface
from reqstool.locations.maven_location import MavenLocation
from reqstool.locations.pypi_location import PypiLocation
from reqstool.model_generators.parsing_config import ParsingConfig
from reqstool.models.generated.requirements_schema import Model as RequirementsPydanticModel
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
        parsing_config: ParsingConfig = ParsingConfig(),
    ):
        self.parent = parent
        self.filename = filename
        self.prefix_with_urn = prefix_with_urn
        self.semantic_validator = semantic_validator
        self.parsing_config = parsing_config
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

        validated = RequirementsPydanticModel.model_validate(data)

        r_metadata: MetaData = self.__parse_metadata(validated)

        r_implementations: List[ImplementationDataInterface] = []
        r_imports: List[ImportDataInterface] = []
        r_requirements: Dict[str, RequirementData] = {}
        r_filters: Dict[str, RequirementFilter] = {}

        source_lines = self.__capture_source_lines(response.text) if self.parsing_config.include_line_numbers else {}

        self.prefix_with_urn = False
        r_imports = self.__parse_imports(validated)
        r_filters = self.__parse_requirement_filters(data=data)
        r_implementations = self.__parse_implementations(validated)
        r_requirements = self.__parse_requirements(validated, data=data, source_lines=source_lines)

        return RequirementsData(
            metadata=r_metadata,
            implementations=r_implementations,
            imports=r_imports,
            requirements=r_requirements,
            filters=r_filters,
        )

    def __parse_metadata(self, model):
        r_urn: str = model.metadata.urn
        r_variant = VARIANTS(model.metadata.variant.value) if model.metadata.variant else None
        r_title: str = model.metadata.title
        r_url: str = model.metadata.url

        return MetaData(urn=r_urn, variant=r_variant, title=r_title, url=r_url)

    def __parse_implementations(self, model):
        locations = []

        if model.implementations is not None:
            self.__parse_location_local(
                locations_obj=model.implementations,
                instance_type=LocalImplData,
                locations=locations,
            )
            self.__parse_location_git(
                locations_obj=model.implementations,
                instance_type=GitImplData,
                locations=locations,
            )
            self.__parse_location_maven(
                locations_obj=model.implementations,
                instance_type=MavenImplData,
                locations=locations,
            )
            self.__parse_location_pypi(
                locations_obj=model.implementations,
                instance_type=PypiImplData,
                locations=locations,
            )

        return locations

    def __parse_imports(self, model):
        locations = []

        if model.imports is not None:
            self.__parse_location_local(
                locations_obj=model.imports,
                instance_type=LocalImportData,
                locations=locations,
            )
            self.__parse_location_git(
                locations_obj=model.imports,
                instance_type=GitImportData,
                locations=locations,
            )
            self.__parse_location_maven(
                locations_obj=model.imports,
                instance_type=MavenImportData,
                locations=locations,
            )
            self.__parse_location_pypi(
                locations_obj=model.imports,
                instance_type=PypiImportData,
                locations=locations,
            )

        return locations

    def __parse_location_maven(self, locations_obj, instance_type, locations):
        if locations_obj.maven is not None:
            for maven in locations_obj.maven:
                MAVEN_CENTRAL_REPO_URL: str = "https://repo.maven.apache.org/maven2/"

                maven_location = instance_type(
                    parent=self.parent,
                    current_unresolved=MavenLocation(
                        env_token=maven.env_token,
                        url=maven.url.root if maven.url else MAVEN_CENTRAL_REPO_URL,
                        group_id=maven.group_id,
                        artifact_id=maven.artifact_id,
                        version=maven.version,
                        classifier=maven.classifier if maven.classifier else "reqstool",
                    ),
                )

                locations.append(maven_location)

    def __parse_location_pypi(self, locations_obj, instance_type, locations):
        if locations_obj.pypi is not None:
            for pypi in locations_obj.pypi:
                PYPI_ORG_SIMPLE_API_URL: str = "https://pypi.org/simple/"

                pypi_location = instance_type(
                    parent=self.parent,
                    current_unresolved=PypiLocation(
                        env_token=pypi.env_token,
                        url=pypi.url.root if pypi.url else PYPI_ORG_SIMPLE_API_URL,
                        package=pypi.package,
                        version=pypi.version,
                    ),
                )

                locations.append(pypi_location)

    def __parse_location_local(self, locations_obj, instance_type, locations):
        if locations_obj.local is not None:
            for local in locations_obj.local:
                local_location = instance_type(parent=self.parent, current_unresolved=LocalLocation(path=local.path))

                locations.append(local_location)

    def __parse_location_git(self, locations_obj, instance_type, locations):
        if locations_obj.git is not None:
            for git in locations_obj.git:
                git_location = instance_type(
                    parent=self.parent,
                    current_unresolved=GitLocation(
                        env_token=git.env_token,
                        url=git.url,
                        branch=git.branch,
                        path=git.path or "",
                    ),
                )

                locations.append(git_location)

    def __parse_requirement_filters(self, data) -> Dict[str, RequirementFilter]:
        return parse_filters(
            data=data,
            ids_key="requirement_ids",
            filter_cls=RequirementFilter,
            validate_fn=self.semantic_validator._validate_req_imports_filter_has_excludes_xor_includes,
        )

    @staticmethod
    def __capture_source_lines(text: str) -> Dict[str, tuple[int, int, int]]:
        rt_yaml = YAML(typ="rt")
        rt_data = rt_yaml.load(text)
        result: Dict[str, tuple[int, int, int]] = {}
        if rt_data is None or "requirements" not in rt_data:
            return result
        reqs = rt_data["requirements"]
        if reqs is None:
            return result
        for idx, item in enumerate(reqs):
            if not hasattr(reqs, "lc"):
                break
            if not isinstance(item, dict) or "id" not in item:
                continue
            id_text = str(item["id"])
            id_line, id_col = item.lc.value("id")
            result[id_text] = (id_line, id_col, id_col + len(id_text))
        return result

    @Requirements("REQ_004", "REQ_036")
    def __parse_requirements(self, model, data, source_lines: Dict[str, tuple[int, int, int]]):  # NOSONAR
        r_reqs = {}

        self.semantic_validator._validate_no_duplicate_requirement_ids(data=data)

        if model.requirements is not None:
            urn = model.metadata.urn

            for req in model.requirements:
                refs_data = []

                if req.references is not None:
                    refs_data.extend(
                        [
                            ReferenceData(
                                requirement_ids=Utils.convert_ids_to_urn_id(
                                    ids=[uid.root for uid in req.references.requirement_ids], urn=urn
                                )
                            )
                        ]
                    )

                rationale = req.rationale
                implementation = req.implementation.value if req.implementation else IMPLEMENTATION.IN_CODE.value
                urn_id = UrnId(urn=urn, id=req.id)
                req_data = RequirementData(
                    id=urn_id,
                    title=req.title,
                    significance=SIGNIFICANCETYPES(req.significance.value),
                    description=req.description,
                    rationale=rationale,
                    implementation=IMPLEMENTATION(implementation),
                    categories=[CATEGORIES(c.value) for c in req.categories],
                    references=refs_data,
                    revision=Utils.parse_version(version_str=req.revision, urn_id=urn_id),
                    lifecycle=LifecycleData.from_dict(
                        {"state": req.lifecycle.state.value, "reason": req.lifecycle.reason} if req.lifecycle else None
                    ),
                    source_line=source_lines[req.id][0] if req.id in source_lines else None,
                    source_col_start=source_lines[req.id][1] if req.id in source_lines else None,
                    source_col_end=source_lines[req.id][2] if req.id in source_lines else None,
                )

                if req_data.id not in r_reqs:
                    r_reqs[req_data.id] = req_data

        return r_reqs
