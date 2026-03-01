# Copyright © LFV

import logging
from dataclasses import dataclass, replace
from typing import Dict, List, Set, Tuple

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.expression_languages.requirements_el import RequirementsELTransformer
from reqstool.expression_languages.svcs_el import SVCsELTransformer
from reqstool.filters.id_filters import IDFilters
from reqstool.filters.requirements_filters import RequirementFilter
from reqstool.filters.svcs_filters import SVCFilter
from reqstool.models.mvrs import MVRData
from reqstool.models.raw_datasets import CombinedRawDataset
from reqstool.models.requirements import VARIANTS, RequirementsData
from reqstool.models.svcs import SVCData, SVCsData


@dataclass(kw_only=True)
class _IndexedDatasetFilterProcessor:
    _crd: CombinedRawDataset

    _requirements: Dict[UrnId, object]  # shared reference
    _svcs: Dict[UrnId, SVCData]  # shared reference
    _mvrs: Dict[UrnId, MVRData]  # shared reference
    _reqs_from_urn: Dict[str, List[UrnId]]  # shared reference
    _svcs_from_req: Dict[UrnId, List[UrnId]]  # shared reference
    _svcs_from_urn: Dict[str, List[UrnId]]  # shared reference
    _mvrs_from_urn: Dict[str, List[UrnId]]  # shared reference
    _mvrs_from_svc: Dict[UrnId, List[UrnId]]  # shared reference
    _accessible_nodes_dict: Dict[str, List[str]]
    _visited_urns_during_filtering: List[str]  # shared reference

    def process_filters(self):
        self.__process_req_filters()
        self.__process_svc_filters()

    @Requirements("REQ_018")
    def __process_req_filters(self):
        logging.debug(f"Starting filtering of requirements from {self._crd.initial_model_urn}")

        kept_requirements, filtered_out_reqs = self.__process_req_filters_per_urn(self._crd.initial_model_urn)

        # use dict comprehension to find requirements to be removed
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
        self, accessible_requirements: set, urn: str, req_filter: RequirementFilter
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
        self, accessible_svcs: set, urn: str, svc_filter: SVCFilter
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
                updated_req_ids = [r for r in svcdata.requirement_ids if r != req_urn_id]
                self._svcs[svc_urn_id] = replace(svcdata, requirement_ids=updated_req_ids)

                # svc is no longer linked to any requirements
                if len(updated_req_ids) == 0:
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
                updated_svc_ids = [s for s in mvrdata.svc_ids if s != svc_urn_id]
                self._mvrs[mvr_urn_id] = replace(mvrdata, svc_ids=updated_svc_ids)

                # mvr is no longer linked to any svcs
                if len(updated_svc_ids) == 0:
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
