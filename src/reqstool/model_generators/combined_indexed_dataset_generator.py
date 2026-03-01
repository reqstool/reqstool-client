# Copyright © LFV

import logging
from dataclasses import dataclass, field, replace
from typing import Dict, List, Set, Tuple

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.utils import Utils
from reqstool.common.validators.lifecycle_validator import LifecycleValidator
from reqstool.expression_languages.requirements_el import RequirementsELTransformer
from reqstool.expression_languages.svcs_el import SVCsELTransformer
from reqstool.filters.id_filters import IDFilters
from reqstool.filters.requirements_filters import RequirementFilter
from reqstool.filters.svcs_filters import SVCFilter
from reqstool.models.annotations import AnnotationData
from reqstool.models.combined_indexed_dataset import CombinedIndexedDataset
from reqstool.models.mvrs import MVRData
from reqstool.models.raw_datasets import CombinedRawDataset
from reqstool.models.requirements import VARIANTS, RequirementData, RequirementsData
from reqstool.models.svcs import SVCData, SVCsData
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
            self.__process_filters()

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

    def __process_filters(self):
        self.__process_req_filters()
        self.__process_svc_filters()

    @Requirements("REQ_018")
    def __process_req_filters(self):
        logging.debug(f"Starting filtering of requirements from {self._crd.initial_model_urn}")

        kept_requirements, filtered_out_reqs = self.__process_req_filters_per_urn(self._crd.initial_model_urn)

        # use dict comphrehension to find requirements to be removed
        filtered_out_reqs: List[UrnId] = [
            req_urn_id for req_urn_id in self._requirements.keys() if req_urn_id not in kept_requirements
        ]

        logging.debug(f"Deleting {len(filtered_out_reqs)} requirements")
        logging.debug(f"Deleting requirements: {filtered_out_reqs}")

        for req_urn_id in filtered_out_reqs:
            self.__delete_requirement(req_urn_id)

        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(f"Requirements left after filtering: {len(self._requirements)}")

            for req_urn_id in self._requirements.keys():
                logging.debug(f"{req_urn_id.urn}:{req_urn_id.id}")

        """_summary_
            returns UrnIds for remaining requirement
        """

    def __process_req_filters_per_urn(self, urn: str) -> Tuple[Set[UrnId], Set[UrnId]]:
        kept_requirements_imports: Set[UrnId] = set()
        filtered_out_reqs_imports: Set[UrnId] = set()

        # for each import urn where it accessible by initial urn
        for import_urn in self._crd.parsing_graph[urn]:
            if self._crd.raw_datasets[import_urn].requirements_data.metadata.variant == VARIANTS.MICROSERVICE:
                continue

            logging.debug(f"Applying requirements filters for import urn {import_urn}")

            # urns that can be reached from this urn
            accessible_urns = self._accessible_nodes_dict[import_urn]

            logging.debug(f"Import urn {import_urn} has access to the following urns: {accessible_urns}")

            kept_requirements_per_import_urn, filtered_out_reqs_per_import_urn = self.__process_req_filters_per_urn(
                import_urn
            )

            kept_requirements_imports.update(kept_requirements_per_import_urn)
            filtered_out_reqs_imports.update(filtered_out_reqs_per_import_urn)

        filtered_out_reqs: Set[UrnId] = set()

        reqdata: RequirementsData = self._crd.raw_datasets[urn].requirements_data
        for filter_urn, req_filter in reqdata.filters.items():
            accessible_requirements_per_filter_urn = set(
                [
                    accessible_requirement
                    for accessible_requirement in kept_requirements_imports
                    if accessible_requirement.urn == filter_urn
                ]
            )

            # check filters against accessible requirements, log errors if requirements are not found
            # requirements that will log a warning will not be processed.
            self.__check_defined_requirements_in_filter(
                filter=req_filter, accessible_urns=accessible_requirements_per_filter_urn
            )

            filtered_out_reqs_per_filter_urn = self.__get_filtered_out_requirements_for_filter_urn(
                accessible_requirements=accessible_requirements_per_filter_urn,
                urn=filter_urn,
                req_filter=req_filter,
            )

            filtered_out_reqs.update(filtered_out_reqs_per_filter_urn)

        kept_requirements: Set[UrnId] = kept_requirements_imports.difference(filtered_out_reqs)
        kept_requirements.update(self._reqs_from_urn[urn])

        logging.debug(f"URN {urn} kept {len(kept_requirements)} requirements: {kept_requirements}")

        logging.debug(f"URN {urn} filtered out {len(filtered_out_reqs)} requirements: {filtered_out_reqs}")

        filtered_out_reqs.update(filtered_out_reqs_imports)
        logging.debug(f"Total filtered out {len(filtered_out_reqs)} requirements URN {urn} : {filtered_out_reqs}")

        self._visited_urns_during_filtering.append(urn)

        return kept_requirements, filtered_out_reqs

    @Requirements("REQ_020")
    def __get_filtered_out_requirements_for_filter_urn(  # noqa C901 # NOSONAR
        self, accessible_requirements: set[UrnId], urn: str, req_filter: RequirementFilter
    ) -> List[UrnId]:
        logging.debug(f"Applying filter for urn {urn} on {len(accessible_requirements)} accessible reqs: {req_filter}")

        filtered_out_requirements: List[UrnId] = []

        # compute lark_tree if custom imports exists
        tree_custom_imports = (
            None if req_filter.custom_imports is None else RequirementsELTransformer.parse_el(req_filter.custom_imports)
        )
        # compute lark_tree if custom exclude exists
        tree_custom_exclude = (
            None if req_filter.custom_exclude is None else RequirementsELTransformer.parse_el(req_filter.custom_exclude)
        )

        # iterate over _all accessible_ requirements
        # since import/excludes don't have to be for the urn that their under
        # we do have to pass the urn to the expression language transformer
        for req_urn_id in accessible_requirements:
            requirement_data = self._requirements[req_urn_id]
            imports_requirement = True

            if req_filter.urn_ids_excludes or tree_custom_exclude:
                b_custom_exclude = False
                b_ids_excludes = False

                if req_filter.urn_ids_excludes:
                    b_ids_excludes = req_urn_id in req_filter.urn_ids_excludes

                if tree_custom_exclude:
                    b_custom_exclude = RequirementsELTransformer(urn=urn, data=requirement_data).transform(
                        tree_custom_exclude
                    )

                imports_requirement = not (b_ids_excludes or b_custom_exclude)
            elif req_filter.urn_ids_imports or tree_custom_imports:
                b_ids_imports = False
                b_custom_imports = False

                if req_filter.urn_ids_imports:
                    b_ids_imports = req_urn_id in req_filter.urn_ids_imports
                if tree_custom_imports:
                    b_custom_imports = RequirementsELTransformer(urn=urn, data=requirement_data).transform(
                        tree_custom_imports
                    )

                imports_requirement = b_ids_imports or b_custom_imports

            else:
                imports_requirement = True

            if imports_requirement:
                logging.debug(f"Filtering in requirement: {req_urn_id}")
            else:
                logging.debug(f"Filtering OUT requirement: {req_urn_id}")
                filtered_out_requirements.append(req_urn_id)

        return filtered_out_requirements

    @Requirements("REQ_019")
    def __process_svc_filters(self):
        logging.debug(f"Starting filtering of svcs from {self._crd.initial_model_urn}")

        kept_svs, filtered_out_svcs = self.__process_svc_filters_per_urn(self._crd.initial_model_urn)

        logging.debug(f"Deleting {len(filtered_out_svcs)} svcs")
        logging.debug(f"Deleting svcs: {filtered_out_svcs}")

        for svc_urn_id in filtered_out_svcs:
            self.__delete_svc(svc_urn_id)

        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(f"SVCs left after filtering: {len(self._svcs)}")

            for svc_urn_id in self._svcs.keys():
                logging.debug(f"{svc_urn_id.urn}:{svc_urn_id.id}")

    def __process_svc_filters_per_urn(self, urn: str) -> Tuple[Set[UrnId], Set[UrnId]]:
        kept_svcs_imports: Set[UrnId] = set()
        filtered_out_svcs_imports: Set[UrnId] = set()

        # for each import urn in the initial urn
        for import_urn in self._crd.parsing_graph[urn]:
            if self._crd.raw_datasets[import_urn].requirements_data.metadata.variant == VARIANTS.MICROSERVICE:
                continue

            logging.debug(f"Applying svcs filters for import urn {import_urn}")

            # urns that can be reached from this urn
            accessible_urns = self._accessible_nodes_dict[import_urn]

            logging.debug(f"Import urn {import_urn} has access to the following urns: {accessible_urns}")

            kept_svcs_per_import_urn, filtered_out_svcs_per_import_urn = self.__process_svc_filters_per_urn(import_urn)

            kept_svcs_imports.update(kept_svcs_per_import_urn)
            filtered_out_svcs_imports.update(filtered_out_svcs_per_import_urn)

        filtered_out_svcs: Set[UrnId] = set()

        svcdata: SVCsData = self._crd.raw_datasets[urn].svcs_data
        if svcdata:
            for filter_urn, svc_filter in svcdata.filters.items():
                accessible_svcs_per_filter_urn = set(
                    [accessible_svc for accessible_svc in kept_svcs_imports if accessible_svc.urn == filter_urn]
                )

                # check filters against accessible requirements, log errors if requirements are not found
                # svcs that will log a warning will not be processed.
                self.__check_defined_requirements_in_filter(
                    filter=svc_filter, accessible_urns=accessible_svcs_per_filter_urn
                )

                filtered_out_svcs_per_filter_urn = self.__get_filtered_out_svcs_for_filter_urn(
                    accessible_svcs=accessible_svcs_per_filter_urn,
                    urn=filter_urn,
                    svc_filter=svc_filter,
                )

                filtered_out_svcs.update(filtered_out_svcs_per_filter_urn)

        kept_svcs = kept_svcs_imports.difference(filtered_out_svcs)
        kept_svcs.update(self._svcs_from_urn.get(urn, []))

        logging.debug(f"URN {urn} kept {len(kept_svcs)} svcs: {kept_svcs}")

        logging.debug(f"URN {urn} filtered out {len(filtered_out_svcs)} svcs: {filtered_out_svcs}")

        filtered_out_svcs.update(filtered_out_svcs_imports)
        logging.debug(f"Total filtered out {len(filtered_out_svcs)} svcs URN {urn} : {filtered_out_svcs}")

        return kept_svcs, filtered_out_svcs

    @Requirements("REQ_020")
    def __get_filtered_out_svcs_for_filter_urn(  # noqa C901 # NOSONAR
        self, accessible_svcs: set[UrnId], urn: str, svc_filter: SVCFilter
    ) -> List[UrnId]:
        logging.debug(f"Applying filter for urn {urn} on {len(accessible_svcs)} accessible svcs: {svc_filter}")

        filtered_out_svcs: List[UrnId] = []

        # compute lark_tree if custom imports exists
        tree_custom_imports = (
            None if svc_filter.custom_imports is None else SVCsELTransformer.parse_el(svc_filter.custom_imports)
        )
        # compute lark_tree if custom exclude exists
        tree_custom_exclude = (
            None if svc_filter.custom_exclude is None else SVCsELTransformer.parse_el(svc_filter.custom_exclude)
        )

        # iterate over _all accessible_ svcs
        # since imports/excludes don't have to be for the urn that their under
        # we do have to pass the urn to the expression language transformer
        for svc_urn_id in accessible_svcs:
            svc_data = self._svcs[svc_urn_id]
            imports_svc = True

            if svc_filter.urn_ids_excludes or tree_custom_exclude:
                b_custom_exclude = False
                b_ids_excludes = False

                if svc_filter.urn_ids_excludes:
                    b_ids_excludes = svc_urn_id in svc_filter.urn_ids_excludes

                if tree_custom_exclude:
                    b_custom_exclude = SVCsELTransformer(urn=urn, data=svc_data).transform(tree_custom_exclude)

                imports_svc = not (b_ids_excludes or b_custom_exclude)
            elif svc_filter.urn_ids_imports or tree_custom_imports:
                b_ids_imports = False
                b_custom_imports = False

                if svc_filter.urn_ids_imports:
                    b_ids_imports = svc_urn_id in svc_filter.urn_ids_imports
                if tree_custom_imports:
                    b_custom_imports = SVCsELTransformer(urn=urn, data=svc_data).transform(tree_custom_imports)

                imports_svc = b_ids_imports or b_custom_imports

            else:
                imports_svc = True

            if imports_svc:
                logging.debug(f"Filtering in svcs: {svc_urn_id}")
            else:
                logging.debug(f"Filtering OUT svcs: {svc_urn_id}")
                filtered_out_svcs.append(svc_urn_id)

        return filtered_out_svcs

    def __delete_requirement(self, req_urn_id: UrnId):
        logging.debug(f"Deleting requirement: {req_urn_id}")

        # 1 remove from datastructure
        del self._requirements[req_urn_id]

        # 2 remove from req_from_urn
        self._reqs_from_urn[req_urn_id.urn].remove(req_urn_id)

        # what svcs are linked to this requirement if any
        if req_urn_id in self._svcs_from_req:
            for svc_urn_id in self._svcs_from_req[req_urn_id]:
                # remove requirement from each such svc and if last req also remove svc
                svcdata = self._svcs[svc_urn_id]
                svcdata.requirement_ids.remove(req_urn_id)

                # svc in no longer linked to any requirements
                if len(svcdata.requirement_ids) == 0:
                    self.__delete_svc(svc_urn_id)

    def __delete_svc(self, svc_urn_id: UrnId):
        logging.debug(f"Deleting svc: {svc_urn_id}")
        # 1 remove from datastructure
        svcdata = self._svcs[svc_urn_id]
        del self._svcs[svc_urn_id]

        # 2 remove from svcs_from_urn
        self._svcs_from_urn[svc_urn_id.urn].remove(svc_urn_id)

        # 3 remove from svcs_from_req
        for req_urn_id in svcdata.requirement_ids:
            self._svcs_from_req[req_urn_id].remove(svc_urn_id)

        # what mvrs are linked to this svc
        if svc_urn_id in self._mvrs_from_svc:
            for mvr_urn_id in self._mvrs_from_svc[svc_urn_id]:
                # remove svc from each such mvr and if last svc also remove mvr
                mvrdata = self._mvrs[mvr_urn_id]
                mvrdata.svc_ids.remove(svc_urn_id)

                # mvr in no longer linked to any svcs
                if len(mvrdata.svc_ids) == 0:
                    self.__delete_mvr(mvr_urn_id)

    def __delete_mvr(self, mvr_urn_id: UrnId):
        logging.debug(f"Deleting mvr: {mvr_urn_id}")

        # 1 remove from datastructure
        mvrdata = self._mvrs[mvr_urn_id]
        del self._mvrs[mvr_urn_id]

        # 2 remove from mvrs_from_urn
        self._mvrs_from_urn[mvr_urn_id.urn].remove(mvr_urn_id)

        # 3 remove from mvrs_from_svc
        for svc_urn_id in mvrdata.svc_ids:
            self._mvrs_from_svc[svc_urn_id].remove(mvr_urn_id)

    def __check_defined_requirements_in_filter(self, filter: IDFilters, accessible_urns: Set[UrnId]):
        if filter.urn_ids_imports:
            for urn_id in filter.urn_ids_imports:
                if urn_id not in accessible_urns:
                    logging.warning(f"Cannot import: {urn_id} does not exist or is not accessible")
        elif filter.urn_ids_excludes:
            for urn_id in filter.urn_ids_excludes:
                if urn_id not in accessible_urns:
                    logging.warning(f"Cannot exclude: {urn_id} does not exist or is not accessible")
