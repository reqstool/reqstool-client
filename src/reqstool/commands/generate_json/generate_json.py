# Copyright © LFV


import json
import logging
from typing import List, Optional

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.models.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.model_generators.combined_indexed_dataset_generator import CombinedIndexedDatasetGenerator
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.models.combined_indexed_dataset import CombinedIndexedDataset
from reqstool.models.raw_datasets import CombinedRawDataset

logger = logging.getLogger(__name__)


@Requirements("REQ_030")
class GenerateJsonCommand:
    def __init__(
        self,
        location: LocationInterface,
        filter_data: bool,
        req_ids: Optional[List[str]] = None,
        svc_ids: Optional[List[str]] = None,
    ):
        self.__initial_location: LocationInterface = location
        self.__filter_data: bool = filter_data
        self.__req_ids: Optional[List[str]] = req_ids
        self.__svc_ids: Optional[List[str]] = svc_ids
        self.result = self.__run()

    @staticmethod
    def _resolve_ids(raw_ids, default_urn, lookup_dict, label):
        resolved = set()
        if not raw_ids:
            return resolved
        for raw_id in raw_ids:
            uid = UrnId.assure_urn_id(urn=default_urn, id=raw_id)
            if uid not in lookup_dict:
                logger.warning(f"{label} '{raw_id}' (resolved to '{uid}') not found in dataset")
            else:
                resolved.add(uid)
        return resolved

    @staticmethod
    def _filter_index(index, key_filter=None, value_filter=None):
        result = {}
        for key, values in index.items():
            if key_filter and key not in key_filter:
                continue
            kept = [v for v in values if v in value_filter] if value_filter else list(values)
            if kept:
                result[key] = kept
        return result

    @staticmethod
    def _collect_related(source_ids, index, valid_set):
        result = set()
        for source_id in source_ids:
            for related_id in index.get(source_id, []):
                if related_id in valid_set:
                    result.add(related_id)
        return result

    def _filter_by_ids(self, cids: CombinedIndexedDataset) -> CombinedIndexedDataset:
        default_urn = cids.initial_model_urn

        resolved_req_ids = self._resolve_ids(self.__req_ids, default_urn, cids.requirements, "Requirement ID")
        resolved_svc_ids = self._resolve_ids(self.__svc_ids, default_urn, cids.svcs, "SVC ID")

        # Include related SVCs for kept requirements
        resolved_svc_ids |= self._collect_related(resolved_req_ids, cids.svcs_from_req, cids.svcs)

        # Include related MVRs for kept SVCs
        kept_mvr_ids = self._collect_related(resolved_svc_ids, cids.mvrs_from_svc, cids.mvrs)

        # If --svc-ids was provided but --req-ids was not, also include requirements referenced by kept SVCs
        if self.__svc_ids and not self.__req_ids:
            for svc_id in resolved_svc_ids:
                svc_data = cids.svcs.get(svc_id)
                if svc_data:
                    resolved_req_ids |= {rid for rid in svc_data.requirement_ids if rid in cids.requirements}

        return CombinedIndexedDataset(
            initial_model_urn=cids.initial_model_urn,
            urn_parsing_order=cids.urn_parsing_order,
            visited_imports_during_filtering=cids.visited_imports_during_filtering,
            accessible_nodes_dict=cids.accessible_nodes_dict,
            filtered=cids.filtered,
            requirements={k: v for k, v in cids.requirements.items() if k in resolved_req_ids},
            svcs={k: v for k, v in cids.svcs.items() if k in resolved_svc_ids},
            mvrs={k: v for k, v in cids.mvrs.items() if k in kept_mvr_ids},
            annotations_impls={k: v for k, v in cids.annotations_impls.items() if k in resolved_req_ids},
            annotations_tests={k: v for k, v in cids.annotations_tests.items() if k in resolved_svc_ids},
            automated_test_result={k: v for k, v in cids.automated_test_result.items() if k in resolved_svc_ids},
            reqs_from_urn=self._filter_index(cids.reqs_from_urn, value_filter=resolved_req_ids),
            svcs_from_urn=self._filter_index(cids.svcs_from_urn, value_filter=resolved_svc_ids),
            svcs_from_req=self._filter_index(
                cids.svcs_from_req, key_filter=resolved_req_ids, value_filter=resolved_svc_ids
            ),
            mvrs_from_urn=self._filter_index(cids.mvrs_from_urn, value_filter=kept_mvr_ids),
            mvrs_from_svc=self._filter_index(
                cids.mvrs_from_svc, key_filter=resolved_svc_ids, value_filter=kept_mvr_ids
            ),
        )

    def __run(self) -> str:
        """Generates The imported models as raw JSON

        Returns:
            str: The imported models as raw JSON.
        """
        holder = ValidationErrorHolder()
        semantic_validator = SemanticValidator(validation_error_holder=holder)
        combined_raw_datasets: CombinedRawDataset = CombinedRawDatasetsGenerator(
            initial_location=self.__initial_location, semantic_validator=semantic_validator
        ).combined_raw_datasets

        cids = CombinedIndexedDatasetGenerator(
            _crd=combined_raw_datasets, _filtered=self.__filter_data
        ).combined_indexed_dataset

        if self.__req_ids or self.__svc_ids:
            cids = self._filter_by_ids(cids)

        return json.dumps(cids.model_dump(mode="json"), separators=(", ", ": "))
