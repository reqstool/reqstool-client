# Copyright © LFV

import sys
from typing import Dict

from ruamel.yaml import YAML

from reqstool.commands.exit_codes import EXIT_CODE_SYNTAX_VALIDATION_ERROR
from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.utils import Utils
from reqstool.common.validators.syntax_validator import JsonSchemaTypes, SyntaxValidator
from reqstool.models.mvrs import MVRData, MVRsData


class MVRsModelGenerator:
    def __init__(self, uri: str, urn: str):
        self.uri = uri
        self.urn = urn
        self.model = self.__generate(uri)

    def __generate(self, uri: str) -> MVRsData:
        response = Utils.open_file_https_file(uri)

        yaml = YAML(typ="safe")

        data: dict = yaml.load(response.text)

        if not SyntaxValidator.is_valid_data(
            json_schema_type=JsonSchemaTypes.MANUAL_VERIFICATION_RESULTS, data=data, urn=self.urn
        ):
            sys.exit(EXIT_CODE_SYNTAX_VALIDATION_ERROR)

        results = self.__parse_mvrs(data)

        return MVRsData(results=results)

    def __parse_mvrs(self, data) -> Dict[UrnId, MVRData]:
        r_result = {}

        for result in data["results"]:
            urn_id = Utils.convert_id_to_urn_id(urn=self.urn, id=result["id"])
            mvr = MVRData(
                id=urn_id,
                svc_ids=Utils.convert_ids_to_urn_id(ids=result["svc_ids"], urn=self.urn),
                comment=result.get("comment"),
                passed=result["pass"],
            )

            r_result[mvr.id] = mvr

        return r_result
