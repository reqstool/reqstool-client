# Copyright © LFV

import sys
from typing import Dict, Optional, Set

from ruamel.yaml import YAML

from reqstool.commands.exit_codes import EXIT_CODE_SYNTAX_VALIDATION_ERROR
from reqstool.common.models.lifecycle import LifecycleData
from reqstool.common.models.urn_id import UrnId
from reqstool.common.utils import Utils
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.common.validators.syntax_validator import JsonSchemaTypes, SyntaxValidator
from reqstool.filters.svcs_filters import SVCFilter
from reqstool.models.generated.software_verification_cases_schema import Model as SVCsPydanticModel
from reqstool.models.svcs import VERIFICATIONTYPES, SVCData, SVCsData


class SVCsModelGenerator:
    def __init__(self, uri: str, semantic_validator: SemanticValidator, urn: str):
        self.uri = uri
        self.semantic_validator = semantic_validator
        self.urn = urn
        self.model = self.__generate(uri)

    def __generate(self, uri: str) -> SVCsData:
        response = Utils.open_file_https_file(uri)

        yaml = YAML(typ="safe")

        data: dict = yaml.load(response.text)

        if not SyntaxValidator.is_valid_data(
            json_schema_type=JsonSchemaTypes.SOFTWARE_VERIFICATION_CASES, data=data, urn=self.urn
        ):
            sys.exit(EXIT_CODE_SYNTAX_VALIDATION_ERROR)

        # Semantic validation still operates on raw dict
        self.semantic_validator._validate_no_duplicate_svc_ids(data=data)

        validated = SVCsPydanticModel.model_validate(data)

        cases = self.__parse_svcs(validated)
        filters = self.__parse_svc_filters(data)

        return SVCsData(cases=cases, filters=filters)

    def __parse_svcs(self, validated: SVCsPydanticModel) -> dict[UrnId, SVCData]:
        r_result = {}

        for case in validated.cases:
            urn_id = UrnId(urn=self.urn, id=case.id)

            svc = SVCData(
                id=urn_id,
                requirement_ids=Utils.convert_ids_to_urn_id(ids=[uid.root for uid in case.requirement_ids], urn=self.urn),
                title=case.title,
                description=case.description,
                verification=VERIFICATIONTYPES(case.verification.value),
                instructions=case.instructions,
                revision=Utils.parse_version(version_str=case.revision, urn_id=urn_id),
                lifecycle=LifecycleData.from_dict(
                    {"state": case.lifecycle.state.value, "reason": case.lifecycle.reason} if case.lifecycle else None
                ),
            )

            if svc.id not in r_result:
                r_result[svc.id] = svc

        return r_result

    def __parse_svc_filters(self, data) -> Dict[str, SVCFilter]:  # NOSONAR
        r_filters = {}

        self.semantic_validator._validate_svc_imports_filter_has_excludes_xor_includes(data)

        if "filters" in data:
            for urn in data["filters"].keys():
                urn_filter = data["filters"][urn]

                svc_urn_ids_includes: Optional[Set[UrnId]] = None
                svc_urn_ids_excludes: Optional[Set[UrnId]] = None
                custom_includes = None
                custom_exclude = None

                if "svc_ids" in urn_filter:
                    if "includes" in urn_filter["svc_ids"]:
                        svc_ids_includes = set(
                            Utils.check_ids_to_filter(current_urn=urn, ids=urn_filter["svc_ids"]["includes"])
                        )
                        svc_urn_ids_includes = set(Utils.convert_ids_to_urn_id(urn=urn, ids=svc_ids_includes))

                    if "excludes" in urn_filter["svc_ids"]:
                        svc_ids_excludes = set(
                            Utils.check_ids_to_filter(current_urn=urn, ids=urn_filter["svc_ids"]["excludes"])
                        )
                        svc_urn_ids_excludes = set(Utils.convert_ids_to_urn_id(urn=urn, ids=svc_ids_excludes))

                if "custom" in urn_filter:
                    if "includes" in urn_filter["custom"]:
                        custom_includes = urn_filter["custom"]["includes"]

                    if "excludes" in urn_filter["custom"]:
                        custom_exclude = urn_filter["custom"]["excludes"]

                svc_filter = SVCFilter(
                    urn_ids_imports=svc_urn_ids_includes,
                    urn_ids_excludes=svc_urn_ids_excludes,
                    custom_imports=custom_includes,
                    custom_exclude=custom_exclude,
                )

                r_filters[urn] = svc_filter

        return r_filters
