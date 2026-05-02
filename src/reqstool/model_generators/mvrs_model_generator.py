# Copyright © LFV

import sys
from typing import Dict

from ruamel.yaml import YAML

from reqstool.commands.exit_codes import EXIT_CODE_SYNTAX_VALIDATION_ERROR
from reqstool.common.models.urn_id import UrnId
from reqstool.common.utils import Utils
from reqstool.common.validators.syntax_validator import JsonSchemaTypes, SyntaxValidator
from reqstool.model_generators.parsing_config import ParsingConfig
from reqstool.models.generated.manual_verification_results_schema import Model as MVRsPydanticModel
from reqstool.models.mvrs import MVRData, MVRsData


class MVRsModelGenerator:
    def __init__(self, uri: str, urn: str, parsing_config: ParsingConfig = ParsingConfig()):
        self.uri = uri
        self.urn = urn
        self.parsing_config = parsing_config
        self.model = self.__generate(uri)

    def __generate(self, uri: str) -> MVRsData:
        response = Utils.open_file_https_file(uri)

        yaml = YAML(typ="safe")

        data: dict = yaml.load(response.text)

        if not SyntaxValidator.is_valid_data(
            json_schema_type=JsonSchemaTypes.MANUAL_VERIFICATION_RESULTS, data=data, urn=self.urn
        ):
            sys.exit(EXIT_CODE_SYNTAX_VALIDATION_ERROR)

        validated = MVRsPydanticModel.model_validate(data)

        source_lines = self.__capture_source_lines(response.text) if self.parsing_config.include_line_numbers else {}

        results = self.__parse_mvrs(validated, source_lines)

        return MVRsData(results=results)

    @staticmethod
    def __capture_source_lines(text: str) -> Dict[str, tuple[int, int, int]]:
        rt_yaml = YAML(typ="rt")
        rt_data = rt_yaml.load(text)
        result: Dict[str, tuple[int, int, int]] = {}
        if rt_data is None or "results" not in rt_data:
            return result
        results = rt_data["results"]
        if results is None:
            return result
        for idx, item in enumerate(results):
            if not hasattr(results, "lc"):
                break
            if not isinstance(item, dict) or "id" not in item:
                continue
            id_text = str(item["id"])
            id_line, id_col = item.lc.value("id")
            result[id_text] = (id_line, id_col, id_col + len(id_text))
        return result

    def __parse_mvrs(
        self,
        validated: MVRsPydanticModel,
        source_lines: Dict[str, tuple[int, int, int]],
    ) -> Dict[UrnId, MVRData]:
        r_result = {}

        for result in validated.results:
            urn_id = Utils.convert_id_to_urn_id(urn=self.urn, id=result.id)
            mvr = MVRData(
                id=urn_id,
                svc_ids=Utils.convert_ids_to_urn_id(ids=result.svc_ids, urn=self.urn),
                comment=result.comment,
                passed=result.pass_,
                source_line=source_lines[result.id][0] if result.id in source_lines else None,
                source_col_start=source_lines[result.id][1] if result.id in source_lines else None,
                source_col_end=source_lines[result.id][2] if result.id in source_lines else None,
            )

            r_result[mvr.id] = mvr

        return r_result
