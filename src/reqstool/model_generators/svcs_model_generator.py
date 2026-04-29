# Copyright © LFV

import sys
from typing import Dict

from ruamel.yaml import YAML

from reqstool.commands.exit_codes import EXIT_CODE_SYNTAX_VALIDATION_ERROR
from reqstool.common.filter_parser import parse_filters
from reqstool.common.models.lifecycle import LifecycleData
from reqstool.common.models.urn_id import UrnId
from reqstool.common.utils import Utils
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.common.validators.syntax_validator import JsonSchemaTypes, SyntaxValidator
from reqstool.filters.svcs_filters import SVCFilter
from reqstool.model_generators.parsing_config import ParsingConfig
from reqstool.models.generated.software_verification_cases_schema import Model as SVCsPydanticModel
from reqstool.models.svcs import VERIFICATIONTYPES, SVCData, SVCsData


class SVCsModelGenerator:
    def __init__(
        self,
        uri: str,
        semantic_validator: SemanticValidator,
        urn: str,
        parsing_config: ParsingConfig = ParsingConfig(),
    ):
        self.uri = uri
        self.semantic_validator = semantic_validator
        self.urn = urn
        self.parsing_config = parsing_config
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

        source_lines = self.__capture_source_lines(response.text) if self.parsing_config.include_line_numbers else {}

        cases = self.__parse_svcs(validated, source_lines)
        filters = self.__parse_svc_filters(data)

        return SVCsData(cases=cases, filters=filters)

    @staticmethod
    def __capture_source_lines(text: str) -> Dict[str, tuple[int, int, int]]:
        rt_yaml = YAML(typ="rt")
        rt_data = rt_yaml.load(text)
        result: Dict[str, tuple[int, int, int]] = {}
        if rt_data is None or "cases" not in rt_data:
            return result
        cases = rt_data["cases"]
        if cases is None:
            return result
        for idx, item in enumerate(cases):
            if not hasattr(cases, "lc"):
                break
            if not isinstance(item, dict) or "id" not in item:
                continue
            id_text = str(item["id"])
            id_line, id_col = item.lc.value("id")
            result[id_text] = (id_line, id_col, id_col + len(id_text))
        return result

    def __parse_svcs(
        self,
        validated: SVCsPydanticModel,
        source_lines: Dict[str, tuple[int, int, int]],
    ) -> dict[UrnId, SVCData]:
        r_result = {}

        for case in validated.cases:
            urn_id = UrnId(urn=self.urn, id=case.id)

            svc = SVCData(
                id=urn_id,
                requirement_ids=Utils.convert_ids_to_urn_id(
                    ids=[uid.root for uid in case.requirement_ids], urn=self.urn
                ),
                title=case.title,
                description=case.description,
                verification=VERIFICATIONTYPES(case.verification.value),
                instructions=case.instructions,
                revision=Utils.parse_version(version_str=case.revision, urn_id=urn_id),
                lifecycle=LifecycleData.from_dict(
                    {"state": case.lifecycle.state.value, "reason": case.lifecycle.reason} if case.lifecycle else None
                ),
                source_line=source_lines[case.id][0] if case.id in source_lines else None,
                source_col_start=source_lines[case.id][1] if case.id in source_lines else None,
                source_col_end=source_lines[case.id][2] if case.id in source_lines else None,
            )

            if svc.id not in r_result:
                r_result[svc.id] = svc

        return r_result

    def __parse_svc_filters(self, data) -> Dict[str, SVCFilter]:
        return parse_filters(
            data=data,
            ids_key="svc_ids",
            filter_cls=SVCFilter,
            validate_fn=self.semantic_validator._validate_svc_imports_filter_has_excludes_xor_includes,
        )
