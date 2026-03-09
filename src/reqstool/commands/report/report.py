# Copyright © LFV

from enum import Enum
from typing import Dict, List, Union

from jinja2 import Template
from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.commands.report.criterias.group_by import GroupbyOptions, GroupByOrganizor
from reqstool.commands.report.criterias.sort_by import SortByOptions
from reqstool.commands.status.statistics_container import StatisticsContainer
from reqstool.commands.status.statistics_generator import StatisticsGenerator
from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.jinja2 import Jinja2Utils
from reqstool.common.utils import Utils
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.model_generators.combined_indexed_dataset_generator import CombinedIndexedDatasetGenerator
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.models.annotations import AnnotationData
from reqstool.models.combined_indexed_dataset import CombinedIndexedDataset
from reqstool.models.mvrs import MVRData
from reqstool.models.svcs import SVCData
from reqstool.models.test_data import TEST_RUN_STATUS

FORMAT_CONFIG = {
    "asciidoc": {"template_subdir": "asciidoc", "h1": "= ", "h2": "== "},
    "markdown": {"template_subdir": "markdown", "h1": "# ", "h2": "## "},
}


class Jinja2Templates(Enum):
    REQUIREMENTS = "requirements", "requirements.j2"
    SVCS = "svcs", "svcs.j2"
    ANNOTATION_IMPLS = "annotation_impls", "annotation_impls.j2"
    ANNOTATION_TESTS = "annotation_tests", "annotation_tests.j2"
    MVRS = "mvrs", "mvrs.j2"
    REQ_REFERENCES = "req_references", "req_references.j2"
    TOTAL_STATISTICS = "total_statistics", "total_statistics.j2"

    def __new__(cls, value, filename):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.filename = filename
        obj.jinja2_template = None
        return obj


@Requirements("REQ_032")
class ReportCommand:
    def __init__(
        self,
        location: LocationInterface,
        group_by: GroupbyOptions,
        sort_by: List[SortByOptions],
        format: str = "asciidoc",
    ):
        self.__initial_location: LocationInterface = location
        self.group_by: GroupbyOptions = group_by
        self.sort_by: List[SortByOptions] = sort_by
        self.__format_config = FORMAT_CONFIG[format]
        self.jinja2_templates: Dict[Jinja2Templates, Template] = {
            j2template: Jinja2Utils.create_template(
                template_name=j2template.filename, template_subdir=self.__format_config["template_subdir"]
            )
            for j2template in Jinja2Templates
        }
        self.result = self.__run()

    def __run(self) -> str:
        semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
        # generate datasets
        crd = CombinedRawDatasetsGenerator(
            initial_location=self.__initial_location, semantic_validator=semantic_validator
        ).combined_raw_datasets
        cid: CombinedIndexedDataset = CombinedIndexedDatasetGenerator(_crd=crd, _filtered=True).combined_indexed_dataset

        aggregated_data: Dict[UrnId, Dict[str, Union[str, str]]] = self.__aggregated_requirements_data(cid=cid)

        # build statistics
        statistics: StatisticsContainer = StatisticsGenerator(
            initial_location=self.__initial_location, semantic_validator=semantic_validator
        ).result

        report = self.__generate_report(cid=cid, aggregated_data=aggregated_data, statistics=statistics)

        return report

    def __generate_report(
        self,
        cid: CombinedIndexedDataset,
        aggregated_data: Dict[UrnId, Dict[str, Union[str, Dict[str, str]]]],
        statistics: StatisticsContainer,
    ):
        statistics_table = Jinja2Utils.render(
            data=statistics.total_statistics, template=self.jinja2_templates[Jinja2Templates.TOTAL_STATISTICS]
        )

        grouped_requirements: Dict[str, List[UrnId]] = GroupByOrganizor(
            cid=cid, group_by=self.group_by, sort_by=self.sort_by
        ).grouped_requirements

        template_data: Dict[str, List[str]] = {
            group_by: [self.__extract_template_data(req_template=aggregated_data[urn_id]) for urn_id in urn_ids]
            for group_by, urn_ids in grouped_requirements.items()
        }

        h1 = self.__format_config["h1"]
        h2 = self.__format_config["h2"]

        output: str = f"{h1}REQUIREMENTS DOCUMENTATION\n" + statistics_table

        for group_by in template_data.keys():
            output += f"{h2}{group_by[0].upper() + group_by[1:]}\n"

            for template in template_data[group_by]:

                output += template

        return output

    def __extract_template_data(self, req_template) -> str:
        rendered = ""
        req_as_text = Jinja2Utils.render(
            data=req_template["requirement"], template=self.jinja2_templates[Jinja2Templates.REQUIREMENTS]
        )
        annot_impls_as_text = Jinja2Utils.render(
            data=req_template["impls"], template=self.jinja2_templates[Jinja2Templates.ANNOTATION_IMPLS]
        )
        annot_tests_as_text = Jinja2Utils.render(
            data=req_template["tests"], template=self.jinja2_templates[Jinja2Templates.ANNOTATION_TESTS]
        )
        svcs_as_text = Jinja2Utils.render(
            data=req_template["svcs"], template=self.jinja2_templates[Jinja2Templates.SVCS]
        )
        mvrs_as_text = Jinja2Utils.render(
            data=req_template["mvrs"], template=self.jinja2_templates[Jinja2Templates.MVRS]
        )
        rendered += (
            req_as_text
            + (annot_impls_as_text if annot_impls_as_text else "")
            + (svcs_as_text if svcs_as_text else "")
            + (annot_tests_as_text if annot_tests_as_text else "")
            + (mvrs_as_text if mvrs_as_text else "")
            + "\n"
        )

        return rendered

    def __aggregated_requirements_data(
        self, cid: CombinedIndexedDataset
    ) -> Dict[UrnId, Dict[str, Union[str, Dict[str, str]]]]:
        requirement_data: Dict[UrnId, Dict[str, Union[str, Dict[str, str]]]] = {}

        for urn_id, req_data in cid.requirements.items():
            # Get all svc UrnIds related to current requirement
            svcs_urn_ids: List[UrnId] = cid.svcs_from_req.get(urn_id, [])

            # Get svcs for current requirement
            svcs: List[SVCData] = [cid.svcs[urn_id] for urn_id in svcs_urn_ids]

            # Get all verification types for current req
            verifications_as_string = ", ".join(str(svc.verification.value) for svc in svcs)

            # get all implementations for current requirement
            impls: List = self._get_annotation_impls(cid=cid, urn_id=urn_id)

            mvr_ids: List[UrnId] = Utils.get_mvr_urn_ids_for_svcs_urn_id(cid=cid, svcs_urn_ids=svcs_urn_ids)

            # Get mvrs for current requirement if there are any (else [])
            mvrs: List[MVRData] = [cid.mvrs[mvr_id] for mvr_id in mvr_ids] if mvr_ids else []

            # generate templates for tests related to current requirement
            automated_test_results: List = self._get_annotated_automated_test_results_for_req(
                cid=cid, svcs_urn_ids=svcs_urn_ids
            )

            req_temp_data = {
                "id": urn_id.id,
                "categories": req_data.categories,
                "description": req_data.description,
                "rationale": req_data.rationale,
                "references": ", ".join(
                    f"{urn_id.urn}:{urn_id.id}"
                    for reference in req_data.references
                    for urn_id in reference.requirement_ids
                ),
                "revision": req_data.revision,
                "significance": req_data.significance.value,
                "title": req_data.title,
                "verification": verifications_as_string,
            }

            data_container = {
                "urn": urn_id.urn,
                "requirement": req_temp_data,
                "impls": impls,
                "svcs": svcs,
                "tests": automated_test_results,
                "mvrs": mvrs,
            }

            requirement_data[urn_id] = data_container

        return requirement_data

    def _get_annotated_automated_test_results_for_req(
        self,
        cid: CombinedIndexedDataset,
        svcs_urn_ids: List[UrnId],
    ) -> List:
        automated_test_results = []
        for urn_id in svcs_urn_ids:
            if urn_id in cid.annotations_tests:
                annotations = cid.annotations_tests[urn_id]
                for test in annotations:
                    test_urn_id = UrnId(urn=urn_id.urn, id=test.fully_qualified_name)
                    results = self.__get_annotated_test_results(cid=cid, urn_id=test_urn_id)
                    results_as_string = ", ".join(str(result.status.value) for result in results)
                    annot_test = {
                        "svc_id": urn_id.id,
                        "element_kind": test.element_kind,
                        "fqn": test.fully_qualified_name,
                        "test_result": results_as_string,
                    }
                    automated_test_results.append(annot_test)

        return automated_test_results

    def __get_annotated_test_results(self, cid: CombinedIndexedDataset, urn_id: UrnId) -> List[TEST_RUN_STATUS]:
        test_results: List[TEST_RUN_STATUS] = []
        # do lookup for each test from previous method, and if result is missing, add a Missing status
        if urn_id in cid.automated_test_result:
            tests = cid.automated_test_result[urn_id]
            for test in tests:
                test_results.append(test)
        else:
            test_results.append(TEST_RUN_STATUS.MISSING)

        return test_results

    def _get_annotation_impls(self, cid: CombinedIndexedDataset, urn_id: UrnId):
        impls_list = []
        impls_for_urn: List[AnnotationData] = cid.annotations_impls[urn_id] if urn_id in cid.annotations_impls else []
        if impls_for_urn:
            for impl in impls_for_urn:
                impl_template = {"element_kind": impl.element_kind, "fqn": impl.fully_qualified_name}
                impls_list.append(impl_template)

        return impls_list
