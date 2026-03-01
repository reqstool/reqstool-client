# Copyright © LFV

import logging
import re
from typing import List

from colorama import Fore, Style
from reqstool_python_decorators.decorators.decorators import Requirements
from tabulate import tabulate

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.utils import Utils
from reqstool.common.validator_error_holder import ValidationError, ValidationErrorHolder
from reqstool.models.imports import ImportDataInterface
from reqstool.models.raw_datasets import CombinedRawDataset
from reqstool.models.requirements import RequirementData
from reqstool.models.svcs import SVCData, SVCsData


class SemanticValidator:
    def __init__(self, validation_error_holder: ValidationErrorHolder) -> None:
        self._validation_error_holder = validation_error_holder

    def validate_post_parsing(self, combined_raw_dataset: CombinedRawDataset) -> List[ValidationError]:
        """Validates everything that's not possible to validate during parsing and
        adds potential errors to the validators ErrorHolder

        Args:
            combined_raw_dataset: the parsed models to check for errors

        Returns:
            List[ValidationError]: a list of validation errors found after parsing
        """

        self._validation_error_holder.add_errors(
            self._validate_svc_refers_to_existing_requirement_ids(combined_raw_dataset=combined_raw_dataset)
        )
        self._validation_error_holder.add_errors(
            self._validate_annotation_impls_refers_to_existing_requirement_ids(
                combined_raw_dataset=combined_raw_dataset
            )
        )
        self._validation_error_holder.add_errors(
            self._validate_annotation_tests_refers_to_existing_svc_ids(combined_raw_dataset=combined_raw_dataset)
        )
        self._validation_error_holder.add_errors(
            self._validate_mvr_refers_to_existing_svc_ids(combined_raw_dataset=combined_raw_dataset)
        )

        errors = self._validation_error_holder.get_errors()

        self._log_all_errors()

        return errors

    def _log_all_errors(self):
        errors = self._validation_error_holder.get_errors()
        validation_result = ""
        table_data = []

        if len(errors) > 0:
            validation_result = f"{Fore.RED}FAIL{Style.RESET_ALL}"
            for error in errors:
                table_data.append([re.sub(r"\s+", " ", error.msg.strip("\n"))])
        else:
            validation_result = f"{Fore.GREEN}PASS{Style.RESET_ALL}"

        title = f"\n\nVALIDATION: {validation_result}"
        table = tabulate(tablefmt="fancy_grid", tabular_data=table_data)
        table_with_title = f"{title}\n{table}\n"

        logging.info(table_with_title)

    @Requirements("REQ_022")
    def _validate_no_duplicate_requirement_ids(self, data: RequirementData) -> bool:
        # if there are no requirements or systems defined, add a validation error
        if "requirements" not in data and "systems" not in data:
            urn = data["metadata"]["urn"]
            self._validation_error_holder.add_error(ValidationError(msg=f"No requirements found for (urn: {urn})!"))
        # only look for duplicates if requirements exists
        elif "requirements" in data:
            all_reqs = set()
            for req in data["requirements"]:
                req_id = req["id"]
                if req_id not in all_reqs:
                    all_reqs.add(req_id)
                else:
                    urn = data["metadata"]["urn"]
                    self._validation_error_holder.add_error(
                        ValidationError(
                            msg=f"REQ {req_id} (urn: {urn}) has already been parsed. Value will not be updated."
                        )
                    )

        return self._validation_error_holder.get_no_of_errors() > 0

    @Requirements("REQ_023")
    def _validate_no_duplicate_svc_ids(self, data: SVCData) -> bool:
        if "cases" not in data:
            self._validation_error_holder.add_error(ValidationError(msg="No svc cases found!"))
        else:
            all_svcs = set()
            for case in data["cases"]:
                svc_id = case["id"]
                if svc_id not in all_svcs:
                    all_svcs.add(svc_id)
                else:
                    self._validation_error_holder.add_error(
                        ValidationError(
                            msg=f"""SVC {svc_id} has already been parsed. Value will not be updated.
                            The svc relates to {case['requirement_ids']}
                            """
                        )
                    )

        return self._validation_error_holder.get_no_of_errors() > 0

    @Requirements("REQ_024")
    def _validate_svc_refers_to_existing_requirement_ids(
        self,  # NOSONAR
        combined_raw_dataset: CombinedRawDataset,
    ) -> List[ValidationError]:
        errors: List[ValidationError] = []

        # get urn and model
        for model, model_data in combined_raw_dataset.raw_datasets.items():
            # Continue if model is not inital_urn
            if model != combined_raw_dataset.initial_model_urn:
                continue
            if model_data.svcs_data is not None:
                for svc_urn_id, svc_data in model_data.svcs_data.cases.items():
                    for urn_req_id in svc_data.requirement_ids:
                        if not self._requirement_id_exists(
                            requirement_id=urn_req_id, combined_raw_dataset=combined_raw_dataset
                        ):
                            svc_id = svc_data.id
                            errors.append(
                                ValidationError(
                                    msg=f"""SVC '{self.prettify_urn_id(svc_id)}' refers to
                                    non-existing requirement id: {self.prettify_urn_id(urn_req_id)}
                                    """
                                )
                            )

        return errors

    @Requirements("REQ_024")
    def _validate_annotation_impls_refers_to_existing_requirement_ids(
        self,
        combined_raw_dataset: CombinedRawDataset,
    ) -> List[ValidationError]:
        errors: List[ValidationError] = []
        for model, model_data in combined_raw_dataset.raw_datasets.items():
            # Continue if model is not inital_urn
            if (
                model != combined_raw_dataset.initial_model_urn
                or not model_data.annotations_data
                or not model_data.annotations_data.implementations
            ):
                continue
            for requirement_id in model_data.annotations_data.implementations:
                if not self._requirement_id_exists(
                    requirement_id=requirement_id, combined_raw_dataset=combined_raw_dataset
                ):
                    errors.append(
                        ValidationError(
                            msg=f"""Annotation refers to
                            non-existing requirement id: {self.prettify_urn_id(requirement_id)}
                            """
                        )
                    )

        return errors

    @Requirements("REQ_025")
    def _validate_annotation_tests_refers_to_existing_svc_ids(
        self,
        combined_raw_dataset: CombinedRawDataset,
    ) -> List[ValidationError]:
        errors: List[ValidationError] = []
        for model, model_data in combined_raw_dataset.raw_datasets.items():
            # Continue if no annotations data
            if not model_data.annotations_data:
                continue
            for svc_id in model_data.annotations_data.tests:
                if not self._svc_id_exists(svc_id, combined_raw_dataset=combined_raw_dataset):
                    errors.append(
                        ValidationError(msg=f"Annotation refers to non-existing svc id: {self.prettify_urn_id(svc_id)}")
                    )

        return errors

    @Requirements("REQ_025")
    def _validate_mvr_refers_to_existing_svc_ids(
        self, combined_raw_dataset: CombinedRawDataset
    ) -> List[ValidationError]:
        errors: List[ValidationError] = []
        for model, model_data in combined_raw_dataset.raw_datasets.items():
            # Continue if model is not inital_urn
            if model != combined_raw_dataset.initial_model_urn or not model_data.mvrs_data:
                continue
            for mvr_data in model_data.mvrs_data.results.values():
                for svc_id in mvr_data.svc_ids:
                    if not self._svc_id_exists(svc_id=svc_id, combined_raw_dataset=combined_raw_dataset):
                        errors.append(
                            ValidationError(msg=f"MVR refers to non-existing svc id: {self.prettify_urn_id(svc_id)}")
                        )

        return errors

    def _validate_svc_imports_filter_has_excludes_xor_includes(self, svc_data: SVCsData) -> List[ValidationError]:
        if "filters" in svc_data:
            for urn in svc_data["filters"].keys():
                urn_filter = svc_data["filters"][urn]
                if "includes" in urn_filter["svc_ids"] and "excludes" in urn_filter["svc_ids"]:
                    self._validation_error_holder.add_error(
                        ValidationError(
                            msg=f"""Both imports and exclude filters applied to svc! (urn: {urn})
                            Exclude filter will be used as default
                            """
                        )
                    )
                if "custom" in urn_filter:
                    if "includes" in urn_filter["custom"] and "excludes" in urn_filter["custom"]:
                        self._validation_error_holder.add_error(
                            ValidationError(
                                msg=f"""Both custom imports and exclude filters applied to svc! (urn: {urn})
                                Exclude filter will be used as default
                                """
                            )
                        )

        return self._validation_error_holder.get_no_of_errors() > 0

    def _validate_req_imports_filter_has_excludes_xor_includes(self, req_data: ImportDataInterface) -> bool:
        if "filters" in req_data:
            for urn in req_data["filters"].keys():
                urn_filter = req_data["filters"][urn]
                if "includes" in urn_filter["requirement_ids"] and "excludes" in urn_filter["requirement_ids"]:
                    self._validation_error_holder.add_error(
                        ValidationError(
                            msg=f"""Both imports and exclude filters applied to req! (urn: {urn})
                            Exclude filter will be used as default
                            """
                        )
                    )
                if "custom" in urn_filter:
                    if "includes" in urn_filter["custom"] and "excludes" in urn_filter["custom"]:
                        self._validation_error_holder.add_error(
                            ValidationError(
                                msg=f"""Both custom imports and exclude filters applied to req! (urn: {urn})
                                Exclude filter will be used as default
                                """
                            )
                        )

        return self._validation_error_holder.get_no_of_errors() > 0

    def _requirement_id_exists(self, requirement_id: str, combined_raw_dataset: CombinedRawDataset) -> bool:
        all_reqs = Utils.flatten_all_reqs(raw_datasets=combined_raw_dataset.raw_datasets)
        return requirement_id in all_reqs

    def _svc_id_exists(self, svc_id: str, combined_raw_dataset: CombinedRawDataset) -> bool:
        all_svcs = Utils.flatten_all_svcs(raw_datasets=combined_raw_dataset.raw_datasets)
        return svc_id in all_svcs

    def prettify_urn_id(self, urn_id: UrnId) -> str:
        return f"<{urn_id.urn}:{urn_id.id}>"
