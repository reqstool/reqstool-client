# Copyright © LFV


import json
import logging

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.services.export_service import ExportService
from reqstool.storage.pipeline import build_database
from reqstool.storage.requirements_repository import RequirementsRepository

logger = logging.getLogger(__name__)


@Requirements("REQ_030")
class GenerateJsonCommand:
    def __init__(
        self,
        location: LocationInterface,
        filter_data: bool,
        req_ids: list[str] | None = None,
        svc_ids: list[str] | None = None,
    ):
        self.__initial_location: LocationInterface = location
        self.__filter_data: bool = filter_data
        self.__req_ids: list[str] | None = req_ids
        self.__svc_ids: list[str] | None = svc_ids
        self.result = self.__run()

    def __run(self) -> str:
        holder = ValidationErrorHolder()
        with build_database(
            location=self.__initial_location,
            semantic_validator=SemanticValidator(validation_error_holder=holder),
            filter_data=self.__filter_data,
        ) as (db, _):
            repo = RequirementsRepository(db)
            export_service = ExportService(repo)
            export_dict = export_service.to_export_dict(req_ids=self.__req_ids, svc_ids=self.__svc_ids)
            return json.dumps(export_dict, separators=(", ", ": "))
