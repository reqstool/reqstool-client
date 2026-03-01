# Copyright © LFV

from dataclasses import dataclass, field, replace
from typing import Dict, List, Set

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.utils import Utils
from reqstool.common.validators.lifecycle_validator import LifecycleValidator
from reqstool.model_generators.indexed_dataset_filter_processor import _IndexedDatasetFilterProcessor
from reqstool.models.annotations import AnnotationData
from reqstool.models.combined_indexed_dataset import CombinedIndexedDataset
from reqstool.models.mvrs import MVRData
from reqstool.models.raw_datasets import CombinedRawDataset
from reqstool.models.requirements import VARIANTS, RequirementData
from reqstool.models.svcs import SVCData
from reqstool.models.test_data import TEST_RUN_STATUS, TestData


@dataclass(kw_only=True)
class CombinedIndexedDatasetGenerator:
    combined_indexed_dataset: CombinedIndexedDataset = field(init=False, default=None)

    _crd: CombinedRawDataset

    # key: urn
    _visited_urns_during_filtering: List[str] = field(init=False, default_factory=list)
    __initial_urn_accessible_urns_non_ms: Set[str] = field(init=False, default_factory=set)
    __initial_urn_accessible_urns_ms: Set[str] = field(init=False, default_factory=set)

    # metadata
    _accessible_nodes_dict: Dict[str, List[str]] = field(init=False, default_factory=dict)
    _filtered: bool = field(default=False)

    # datastructures

    _requirements: Dict[UrnId, RequirementData] = field(init=False, default_factory=dict)
    _svcs: Dict[UrnId, SVCData] = field(init=False, default_factory=dict)
    _mvrs: Dict[UrnId, MVRData] = field(init=False, default_factory=dict)

    # annotations have no id
    # key = req urnid
    _annotations_impls: Dict[UrnId, List[AnnotationData]] = field(init=False, default_factory=dict)
    # key = svc urnid
    _annotations_tests: Dict[UrnId, List[AnnotationData]] = field(init=False, default_factory=dict)

    # key = svc urnid
    _automated_test_result: Dict[UrnId, List[TestData]] = field(init=False, default_factory=dict)

    # indexes/lookups

    # requirement indexes
    _reqs_from_urn: Dict[str, List[UrnId]] = field(init=False, default_factory=dict)

    # svc indexes
    _svcs_from_urn: Dict[str, List[UrnId]] = field(init=False, default_factory=dict)
    _svcs_from_req: Dict[UrnId, List[UrnId]] = field(init=False, default_factory=dict)

    # mvr indexes
    _mvrs_from_urn: Dict[str, List[UrnId]] = field(init=False, default_factory=dict)
    _mvrs_from_svc: Dict[UrnId, List[UrnId]] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self._accessible_nodes_dict = Utils.create_accessible_nodes_dict(self._crd.parsing_graph)

        self.combined_indexed_dataset = self.__generate()

    def __generate(self) -> CombinedIndexedDataset:
        self.process()

        return self.__create()

    def __create(self) -> CombinedIndexedDataset:
        combined_indexed_dataset = CombinedIndexedDataset(
            initial_model_urn=self._crd.initial_model_urn,
            urn_parsing_order=self._crd.urn_parsing_order,
            visited_imports_during_filtering=self._visited_urns_during_filtering,
            accessible_nodes_dict=self._accessible_nodes_dict,
            filtered=self._filtered,
            requirements=self._requirements,
            svcs=self._svcs,
            mvrs=self._mvrs,
            annotations_impls=self._annotations_impls,
            annotations_tests=self._annotations_tests,
            automated_test_result=self._automated_test_result,
            reqs_from_urn=self._reqs_from_urn,
            svcs_from_urn=self._svcs_from_urn,
            svcs_from_req=self._svcs_from_req,
            mvrs_from_urn=self._mvrs_from_urn,
            mvrs_from_svc=self._mvrs_from_svc,
        )

        LifecycleValidator(combined_indexed_dataset)

        return combined_indexed_dataset

    def process(self):
        # if initial urn is not a system then do nothing
        self.initial_urn_is_ms = (
            self._crd.raw_datasets[self._crd.initial_model_urn].requirements_data.metadata.variant
            == VARIANTS.MICROSERVICE
        )

        self.__initial_urn_accessible_urns_non_ms: set[str] = {self._crd.initial_model_urn} | {
            node
            for node in self._accessible_nodes_dict[self._crd.initial_model_urn]
            if self._crd.raw_datasets[node].requirements_data.metadata.variant != VARIANTS.MICROSERVICE
        }

        self.__initial_urn_accessible_urns_ms: set[str] = {
            node
            for node in self._accessible_nodes_dict[self._crd.initial_model_urn]
            if self._crd.raw_datasets[node].requirements_data.metadata.variant == VARIANTS.MICROSERVICE
        }

        self.__process_reqs()
        self.__process_svcs()
        self.__process_mvrs()
        self.__process_annotations_impls()
        self.__process_annotations_tests()
        self.__process_automated_test_result()

        if self._filtered:
            _IndexedDatasetFilterProcessor(
                _crd=self._crd,
                _requirements=self._requirements,
                _svcs=self._svcs,
                _mvrs=self._mvrs,
                _reqs_from_urn=self._reqs_from_urn,
                _svcs_from_req=self._svcs_from_req,
                _svcs_from_urn=self._svcs_from_urn,
                _mvrs_from_urn=self._mvrs_from_urn,
                _mvrs_from_svc=self._mvrs_from_svc,
                _accessible_nodes_dict=self._accessible_nodes_dict,
                _visited_urns_during_filtering=self._visited_urns_during_filtering,
            ).process_filters()

    def __is_urn_ms(self, urn: str) -> bool:
        return self._crd.raw_datasets[urn].requirements_data.metadata.variant == VARIANTS.MICROSERVICE

    def __process_reqs(self):
        for urn, rds in self._crd.raw_datasets.items():
            # if requirements defined in then only add if ms is initial urn
            if self.__is_urn_ms(urn) and self._crd.initial_model_urn != urn:
                continue

            self._reqs_from_urn[urn] = []
            for id, reqdata in rds.requirements_data.requirements.items():
                assert id == reqdata.id
                assert reqdata.id not in self._requirements

                self._requirements[reqdata.id] = reqdata
                Utils.append_data_item_to_dict_list_entry(dictionary=self._reqs_from_urn, key=urn, data=reqdata.id)

    def __process_svcs(self):
        for urn, rds in self._crd.raw_datasets.items():
            if rds.svcs_data and rds.svcs_data.cases:
                for id, svcdata in rds.svcs_data.cases.items():
                    assert id == svcdata.id
                    assert svcdata.id not in self._svcs

                    # if urn is ms and urn is initial urn - remove svc references to reqs from not visited urns
                    if self.__is_urn_ms(urn) and self._crd.initial_model_urn != urn:
                        remove_req_ids_from_svcdata: Set[UrnId] = set()
                        for req_urn_id in svcdata.requirement_ids:
                            if req_urn_id.urn not in self.__initial_urn_accessible_urns_non_ms:
                                remove_req_ids_from_svcdata.add(req_urn_id)

                        # if no reqs where removed just add svcdata as is
                        if len(remove_req_ids_from_svcdata) > 0:
                            # remove references to reqs that where not visited
                            kept_requirement_ids = list(
                                set(svcdata.requirement_ids).difference(remove_req_ids_from_svcdata)
                            )

                            # if svcdata no longer references any reqs - do not add
                            if len(kept_requirement_ids) == 0:
                                continue

                            svcdata = replace(svcdata, requirement_ids=kept_requirement_ids)

                    self._svcs[svcdata.id] = svcdata

                    Utils.append_data_item_to_dict_list_entry(dictionary=self._svcs_from_urn, key=urn, data=svcdata.id)

                    for req_urn_id in svcdata.requirement_ids:
                        Utils.append_data_item_to_dict_list_entry(
                            dictionary=self._svcs_from_req,
                            key=req_urn_id,
                            data=svcdata.id,
                        )

    def __process_mvrs(self):
        for urn, rds in self._crd.raw_datasets.items():
            if rds.mvrs_data and rds.mvrs_data.results:
                for mvrid, mvrdata in rds.mvrs_data.results.items():
                    assert mvrdata.id not in self._mvrs

                    # if urn is ms and urn is initial urn - remove mvr references to svc from not visited urns
                    if self.__is_urn_ms(urn) and self._crd.initial_model_urn != urn:
                        remove_svc_ids_from_mvrdata: Set[UrnId] = set()
                        for svc_urn_id in mvrdata.svc_ids:
                            if svc_urn_id.urn not in self.__initial_urn_accessible_urns_non_ms:
                                remove_svc_ids_from_mvrdata.add(svc_urn_id)

                        # if no svcs where removed just add mvrdata as is
                        if len(remove_svc_ids_from_mvrdata) > 0:
                            # remove references to svcs that where not visited
                            kept_svc_ids = list(set(mvrdata.svc_ids).difference(remove_svc_ids_from_mvrdata))

                            # if mvrdata no longer references any reqs - do not add
                            if len(kept_svc_ids) == 0:
                                continue

                            mvrdata = replace(mvrdata, svc_ids=kept_svc_ids)

                    self._mvrs[mvrdata.id] = mvrdata

                    Utils.append_data_item_to_dict_list_entry(dictionary=self._mvrs_from_urn, key=urn, data=mvrdata.id)

                    for svc_urn_id in mvrdata.svc_ids:
                        Utils.append_data_item_to_dict_list_entry(
                            dictionary=self._mvrs_from_svc,
                            key=svc_urn_id,
                            data=mvrdata.id,
                        )

    def __process_annotations_impls(self):
        for urn, rds in self._crd.raw_datasets.items():
            if rds.annotations_data and rds.annotations_data.implementations:
                for req_id, req_anno_data in rds.annotations_data.implementations.items():
                    Utils.append_data_item_to_dict_list_entry(
                        dictionary=self._annotations_impls, key=req_id, data=req_anno_data
                    )

    def __process_annotations_tests(self):
        for urn, rds in self._crd.raw_datasets.items():
            if rds.annotations_data and rds.annotations_data.tests:
                for req_id, req_anno_data in rds.annotations_data.tests.items():
                    Utils.append_data_item_to_dict_list_entry(
                        dictionary=self._annotations_tests, key=req_id, data=req_anno_data
                    )

    def __process_automated_test_result(self):
        for urn, rds in self._crd.raw_datasets.items():
            if rds.annotations_data:
                for urn_id, annotation_data_list in rds.annotations_data.tests.items():
                    for annotation_data in annotation_data_list:
                        svc_urn_id = UrnId(urn=urn_id.urn, id=annotation_data.fully_qualified_name)
                        automated_test_result_urn_id = UrnId(urn=urn, id=annotation_data.fully_qualified_name)

                        # process differently if this is a class based test annotation
                        if annotation_data.element_kind == "CLASS":
                            test_data: TestData = self.__process_class_annotated_test_results(
                                urn=urn, fqn=annotation_data.fully_qualified_name
                            )
                        # check if there is an automated test result for this annotation
                        elif (
                            self._crd.raw_datasets[urn]
                            and self._crd.raw_datasets[urn].automated_tests
                            and automated_test_result_urn_id in self._crd.raw_datasets[urn].automated_tests.tests
                        ):
                            test_data = self._crd.raw_datasets[urn].automated_tests.tests[automated_test_result_urn_id]

                        # since there is an annotation we are missing automated test result
                        else:
                            test_data = TestData(
                                fully_qualified_name=annotation_data.fully_qualified_name,
                                status=TEST_RUN_STATUS.MISSING,
                            )

                        Utils.append_data_item_to_dict_list_entry(
                            dictionary=self._automated_test_result, key=svc_urn_id, data=test_data
                        )

    def __process_class_annotated_test_results(self, urn: str, fqn: str):
        # get all test results that includes the class fqn
        get_all_test_res: [TEST_RUN_STATUS] = [
            self._crd.raw_datasets[urn].automated_tests.tests[urn_id].status
            for urn_id in self._crd.raw_datasets[urn].automated_tests.tests
            if fqn in urn_id.id
        ]

        test_data = None
        # if no entries in list, then the test result(s) are missing.
        if not get_all_test_res:
            test_data = TestData(
                fully_qualified_name=fqn,
                status=TEST_RUN_STATUS.MISSING,
            )
        # if any test in list is failed, then the test should be marked as failed
        elif all(test_res == TEST_RUN_STATUS.PASSED for test_res in get_all_test_res):
            test_data = TestData(
                fully_qualified_name=fqn,
                status=TEST_RUN_STATUS.PASSED,
            )
        else:
            test_data = TestData(
                fully_qualified_name=fqn,
                status=TEST_RUN_STATUS.FAILED,
            )

        return test_data
