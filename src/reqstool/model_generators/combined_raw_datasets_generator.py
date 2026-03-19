# Copyright © LFV

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.exceptions import CircularImportError, MissingRequirementsFileError
from reqstool.common.utils import TempDirectoryUtil, Utils
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.location_resolver.location_resolver import LocationResolver
from reqstool.locations.location import LocationInterface
from reqstool.model_generators.annotations_model_generator import AnnotationsModelGenerator
from reqstool.model_generators.mvrs_model_generator import MVRsModelGenerator
from reqstool.model_generators.requirements_model_generator import RequirementsModelGenerator
from reqstool.model_generators.svcs_model_generator import SVCsModelGenerator
from reqstool.model_generators.testdata_model_generator import TestDataModelGenerator
from reqstool.models.annotations import AnnotationsData
from reqstool.models.implementations import ImplementationDataInterface
from reqstool.models.mvrs import MVRsData
from reqstool.models.raw_datasets import CombinedRawDataset, RawDataset
from reqstool.models.requirements import RequirementsData
from reqstool.models.svcs import SVCsData
from reqstool.models.test_data import TestsData
from reqstool.requirements_indata.requirements_indata import RequirementsIndata
from reqstool.storage.database import RequirementsDatabase


@Requirements("REQ_005", "REQ_006", "REQ_007")
class CombinedRawDatasetsGenerator:
    def __init__(
        self,
        initial_location: LocationInterface,
        semantic_validator: SemanticValidator,
        database: Optional[RequirementsDatabase] = None,
    ):
        self.__level: int = 0
        self.__initial_location_handler: LocationResolver = LocationResolver(
            parent=None, current_unresolved=initial_location
        )
        self.semantic_validator = semantic_validator
        self._parsing_order: List[str] = []
        self._parsing_graph: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self._database = database
        self.combined_raw_datasets = self.__generate()

    def __generate(self) -> CombinedRawDataset:
        # handle initial source
        logging.debug(f"Using temporary path: {TempDirectoryUtil.get_path()}\n")

        raw_datasets: Dict[str, RawDataset] = {}

        initial_imported_model = self.__parse_source(current_location_handler=self.__initial_location_handler)

        initial_urn = initial_imported_model.requirements_data.metadata.urn

        raw_datasets[initial_urn] = initial_imported_model

        # Add inital source to parsing order list
        self._parsing_order.append(initial_urn)

        # handle imported sources
        self.__handle_initial_imports(raw_datasets=raw_datasets, rd=initial_imported_model.requirements_data)

        combined_raw_datasets = CombinedRawDataset(
            initial_model_urn=initial_urn,
            raw_datasets=raw_datasets,
            urn_parsing_order=self._parsing_order,
            parsing_graph=self._parsing_graph,
        )

        self.semantic_validator.validate_post_parsing(combined_raw_dataset=combined_raw_datasets)

        self._populate_database(combined_raw_datasets)

        return combined_raw_datasets

    def _populate_database(self, crd: CombinedRawDataset) -> None:
        if self._database is None:
            return

        self._database.set_metadata("initial_urn", crd.initial_model_urn)

        # Multi-pass insertion to satisfy FK constraints across URNs.
        # Order: requirements → SVCs → MVRs → annotations → test results → graph
        # Each pass is committed as a batch for performance.
        self.__populate_requirements(crd)
        self.__populate_svcs(crd)
        self.__populate_mvrs(crd)
        self.__populate_annotations(crd)
        self.__populate_test_results(crd)
        self.__populate_parsing_graph(crd)
        self._database.commit()

    def __populate_requirements(self, crd: CombinedRawDataset) -> None:
        for urn in crd.urn_parsing_order:
            rd = crd.raw_datasets[urn]
            self._database.insert_urn_metadata(rd.requirements_data.metadata)
            for req_data in rd.requirements_data.requirements.values():
                self._database.insert_requirement(urn, req_data)

    def __populate_svcs(self, crd: CombinedRawDataset) -> None:
        for urn in crd.urn_parsing_order:
            rd = crd.raw_datasets[urn]
            if rd.svcs_data is not None and rd.svcs_data.cases:
                for svc_data in rd.svcs_data.cases.values():
                    self._database.insert_svc(urn, svc_data)

    def __populate_mvrs(self, crd: CombinedRawDataset) -> None:
        for urn in crd.urn_parsing_order:
            rd = crd.raw_datasets[urn]
            if rd.mvrs_data is not None and rd.mvrs_data.results:
                for mvr_data in rd.mvrs_data.results.values():
                    self._database.insert_mvr(urn, mvr_data)

    def __populate_annotations(self, crd: CombinedRawDataset) -> None:
        for urn in crd.urn_parsing_order:
            rd = crd.raw_datasets[urn]
            if rd.annotations_data is not None:
                for req_urn_id, annotations in rd.annotations_data.implementations.items():
                    for annotation in annotations:
                        self._database.insert_annotation_impl(req_urn_id, annotation)
                for svc_urn_id, annotations in rd.annotations_data.tests.items():
                    for annotation in annotations:
                        self._database.insert_annotation_test(svc_urn_id, annotation)

    def __populate_test_results(self, crd: CombinedRawDataset) -> None:
        for urn in crd.urn_parsing_order:
            rd = crd.raw_datasets[urn]
            if rd.automated_tests is not None:
                for test_urn_id, test_data in rd.automated_tests.tests.items():
                    self._database.insert_test_result(test_urn_id.urn, test_data.fully_qualified_name, test_data.status)

    def __populate_parsing_graph(self, crd: CombinedRawDataset) -> None:
        for parent_urn, children in crd.parsing_graph.items():
            for child_urn, edge_type in children:
                self._database.insert_parsing_graph_edge(parent_urn, child_urn, edge_type)

    def __handle_initial_imports(self, raw_datasets: Dict[str, RawDataset], rd: RequirementsData):
        if rd.imports:
            parsed_systems = self.__import_systems(raw_datasets, parent_rd=rd, visited={rd.metadata.urn})
            self._parsing_graph[rd.metadata.urn].extend([(u, "import") for u in parsed_systems])

        if rd.implementations:
            parsed_microservices = self.__import_implementations(raw_datasets, implementations=rd.implementations)
            self._parsing_graph[rd.metadata.urn].extend([(u, "implementation") for u in parsed_microservices])
            for ms_urn in parsed_microservices:
                self._parsing_graph[ms_urn].append((rd.metadata.urn, "implementation"))

    def __import_systems(
        self,
        raw_datasets: Dict[str, RawDataset],
        parent_rd: RequirementsData,
        visited: Optional[Set[str]] = None,
    ) -> List[str]:
        if not parent_rd.imports:
            return []

        if visited is None:
            visited = set()

        self.__level += 1

        parsed_urns: List[str] = []
        for system in parent_rd.imports:
            current_imported_model = self.__parse_source(current_location_handler=system)
            current_urn = current_imported_model.requirements_data.metadata.urn

            if current_urn in visited:
                raise CircularImportError(current_urn, list(visited))

            visited.add(current_urn)

            # add urn to parsing_order_list
            self._parsing_order.append(current_urn)
            parsed_urns.append(current_urn)

            raw_datasets[current_urn] = current_imported_model

            # recursively import systems
            imported_systems = self.__import_systems(
                raw_datasets=raw_datasets, parent_rd=current_imported_model.requirements_data, visited=visited
            )

            self._parsing_graph[current_urn].extend([(u, "import") for u in imported_systems])

        self.__level -= 1

        return parsed_urns

    def __import_implementations(
        self,
        raw_datasets: Dict[str, RawDataset],
        implementations: List[ImplementationDataInterface],
    ) -> List[str]:
        parsed_urns: List[str] = []

        self.__level += 1
        for implementation in implementations:
            parsed_model = self.__parse_source(current_location_handler=implementation)
            current_urn = parsed_model.requirements_data.metadata.urn

            # add urn to parsing_order_list
            self._parsing_order.append(current_urn)
            parsed_urns.append(current_urn)

            raw_datasets[current_urn] = parsed_model

        self.__level -= 1

        return parsed_urns

    @Requirements("REQ_008", "REQ_026")
    def __parse_source(self, current_location_handler: LocationResolver) -> RawDataset:
        annotations_data = None
        svcs_data = None
        mvrs_data = None
        automated_tests = None

        tmp_path = TempDirectoryUtil.get_suffix_path("can_we_use_urn_here").absolute()

        actual_tmp_path = current_location_handler.make_available_on_localdisk(dst_path=tmp_path)

        requirements_indata = RequirementsIndata(dst_path=actual_tmp_path, location=current_location_handler.current)

        if not requirements_indata.requirements_indata_paths.requirements_yml.exists:
            raise MissingRequirementsFileError(path=requirements_indata.requirements_indata_paths.requirements_yml.path)

        rmg = RequirementsModelGenerator(
            parent=current_location_handler.current,
            filename=requirements_indata.requirements_indata_paths.requirements_yml.path,
            prefix_with_urn=False,
            semantic_validator=self.semantic_validator,
        )

        if self.__level > 0:
            logging.info(f"{'*' * self.__level} {requirements_indata.dst_path}")
        else:
            logging.info(f"{requirements_indata.dst_path}")

        # parse file sources other than requirements.yml
        annotations_data, svcs_data, automated_tests, mvrs_data = self.__parse_source_other(
            actual_tmp_path, requirements_indata, rmg
        )

        raw_dataset = RawDataset(
            requirements_data=rmg.requirements_data,
            annotations_data=annotations_data,
            svcs_data=svcs_data,
            mvrs_data=mvrs_data,
            automated_tests=automated_tests,
        )

        return raw_dataset

    @Requirements("REQ_009", "REQ_010", "REQ_013")
    def __parse_source_other(
        self, actual_tmp_path: str, requirements_indata: RequirementsIndata, rmg: RequirementsModelGenerator
    ):
        annotations_data: AnnotationsData = None
        svcs_data: SVCsData = None
        mvrs_data: MVRsData = None
        automated_tests: TestsData = None
        tests = {}
        # get current urn
        current_urn = rmg.requirements_data.metadata.urn

        if requirements_indata.requirements_indata_paths.svcs_yml.exists:
            svcs_data = SVCsModelGenerator(
                uri=requirements_indata.requirements_indata_paths.svcs_yml.path,
                semantic_validator=self.semantic_validator,
                urn=current_urn,
            ).model

        # handle automated test results

        for test_result_pattern in requirements_indata.test_results_patterns:

            test_result_files = Utils.get_matching_files(path=actual_tmp_path, patterns=[test_result_pattern])

            automated_tests_results = TestDataModelGenerator(test_result_files, urn=current_urn).model

            tests |= automated_tests_results.tests

        automated_tests = TestsData(tests=tests)

        # handle manual verification results

        if requirements_indata.requirements_indata_paths.mvrs_yml.exists:
            mvrs_data = MVRsModelGenerator(
                uri=requirements_indata.requirements_indata_paths.mvrs_yml.path, urn=current_urn
            ).model

        # handle annotations
        if requirements_indata.requirements_indata_paths.annotations_yml.exists:
            annotations_data = AnnotationsModelGenerator(
                uri=requirements_indata.requirements_indata_paths.annotations_yml.path, urn=current_urn
            ).model

        return annotations_data, svcs_data, automated_tests, mvrs_data
