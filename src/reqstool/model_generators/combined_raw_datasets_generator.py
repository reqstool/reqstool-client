# Copyright © LFV

import logging
from typing import Dict, List

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.exceptions import MissingRequirementsFileError
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
from reqstool.models.requirements import VARIANTS, RequirementsData
from reqstool.models.svcs import SVCsData
from reqstool.models.test_data import TestsData
from reqstool.requirements_indata.requirements_indata import RequirementsIndata


@Requirements("REQ_005", "REQ_006", "REQ_007")
class CombinedRawDatasetsGenerator:
    def __init__(self, initial_location: LocationInterface, semantic_validator: SemanticValidator):
        self.__level: int = 0
        self.__initial_source_type: VARIANTS = None
        self.__initial_location_handler: LocationResolver = LocationResolver(
            parent=None, _current_unresolved=initial_location
        )
        self.semantic_validator = semantic_validator
        self._parsing_order: List[str] = []
        self._parsing_graph: Dict[str, List[str]] = {}
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

        return combined_raw_datasets

    def __handle_initial_imports(self, raw_datasets: Dict[str, RawDataset], rd: RequirementsData):
        match self.__initial_source_type:
            case VARIANTS.SYSTEM:
                parsed_systems = self.__import_systems(raw_datasets, parent_rd=rd)
                parsed_microservices = self.__import_implementations(raw_datasets, implementations=rd.implementations)
                Utils.extend_data_sequence_to_dict_list_entry(
                    self._parsing_graph, key=rd.metadata.urn, data=parsed_systems
                )
                Utils.extend_data_sequence_to_dict_list_entry(
                    self._parsing_graph, key=rd.metadata.urn, data=parsed_microservices
                )

                # add current urn as parent to all microservices
                for ms_urn in parsed_microservices:
                    Utils.append_data_item_to_dict_list_entry(self._parsing_graph, key=ms_urn, data=rd.metadata.urn)

            case VARIANTS.MICROSERVICE:
                parsed_systems = self.__import_systems(raw_datasets, parent_rd=rd)
                Utils.extend_data_sequence_to_dict_list_entry(
                    self._parsing_graph, key=rd.metadata.urn, data=parsed_systems
                )
            case _:
                raise RuntimeError("Unsupported initial source system type (this should not happen)")

    def __import_systems(self, raw_datasets: Dict[str, RawDataset], parent_rd: RequirementsData) -> List[str]:
        if parent_rd.imports is None:
            return []

        self.__level += 1

        parsed_urns: List[str] = []
        for system in parent_rd.imports:
            current_imported_model = self.__parse_source(current_location_handler=system)
            current_urn = current_imported_model.requirements_data.metadata.urn

            # add urn to parsing_order_list
            self._parsing_order.append(current_urn)
            parsed_urns.append(current_urn)

            raw_datasets[current_urn] = current_imported_model

            assert (
                current_imported_model.requirements_data.metadata.variant == VARIANTS.SYSTEM
                or current_imported_model.requirements_data.metadata.variant == VARIANTS.EXTERNAL
            )

            # if current source type is system or external import systems recursively
            if (
                current_imported_model.requirements_data.metadata.variant == VARIANTS.SYSTEM
                or current_imported_model.requirements_data.metadata.variant == VARIANTS.EXTERNAL
            ):
                imported_systems = self.__import_systems(
                    raw_datasets=raw_datasets, parent_rd=current_imported_model.requirements_data
                )

                Utils.extend_data_sequence_to_dict_list_entry(
                    dictionary=self._parsing_graph, key=current_urn, data=imported_systems
                )

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

        if self.__initial_location_handler is current_location_handler:
            self.__initial_source_type = rmg.requirements_data.metadata.variant

        if (
            rmg.requirements_data.metadata.variant is VARIANTS.SYSTEM
            or rmg.requirements_data.metadata.variant is VARIANTS.MICROSERVICE
        ):
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

            # requirement annotations (impls) - only for microservices
            if rmg.requirements_data.metadata.variant is not VARIANTS.MICROSERVICE:
                assert not annotations_data.implementations

        return annotations_data, svcs_data, automated_tests, mvrs_data
