# Copyright © LFV

from __future__ import annotations

from enum import Enum

from jinja2 import Template
from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.commands.report.criterias.group_by import GroupbyOptions, GroupByOrganizor
from reqstool.commands.report.criterias.sort_by import SortByOptions
from reqstool.common.models.urn_id import UrnId
from reqstool.common.jinja2 import Jinja2Utils
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.models.annotations import AnnotationData
from reqstool.models.mvrs import MVRData
from reqstool.models.svcs import SVCData
from reqstool.models.test_data import TEST_RUN_STATUS
from reqstool.services.statistics_service import StatisticsService
from reqstool.storage.pipeline import build_database
from reqstool.storage.requirements_repository import RequirementsRepository

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
        sort_by: list[SortByOptions],
        format: str = "asciidoc",
    ):
        self.__initial_location: LocationInterface = location
        self.group_by: GroupbyOptions = group_by
        self.sort_by: list[SortByOptions] = sort_by
        self.__format_config = FORMAT_CONFIG[format]
        self.jinja2_templates: dict[Jinja2Templates, Template] = {
            j2template: Jinja2Utils.create_template(
                template_name=j2template.filename, template_subdir=self.__format_config["template_subdir"]
            )
            for j2template in Jinja2Templates
        }
        self.result = self.__run()

    def __run(self) -> str:
        with build_database(
            location=self.__initial_location,
            semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
        ) as (db, _):
            repo = RequirementsRepository(db)

            aggregated_data: dict[UrnId, dict[str, str]] = self.__aggregated_requirements_data(repo=repo)
            stats_service = StatisticsService(repo)

            return self.__generate_report(repo=repo, aggregated_data=aggregated_data, statistics=stats_service)

    def __generate_report(
        self,
        repo: RequirementsRepository,
        aggregated_data: dict[UrnId, dict[str, str | dict[str, str]]],
        statistics: StatisticsService,
    ):
        statistics_table = Jinja2Utils.render(
            data=statistics.total_statistics, template=self.jinja2_templates[Jinja2Templates.TOTAL_STATISTICS]
        )

        grouped_requirements: dict[str, list[UrnId]] = GroupByOrganizor(
            repo=repo, group_by=self.group_by, sort_by=self.sort_by
        ).grouped_requirements

        template_data: dict[str, list[str]] = {
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
        self, repo: RequirementsRepository
    ) -> dict[UrnId, dict[str, str | dict[str, str]]]:
        requirement_data: dict[UrnId, dict[str, str | dict[str, str]]] = {}

        all_requirements = repo.get_all_requirements()
        all_svcs = repo.get_all_svcs()
        all_mvrs = repo.get_all_mvrs()
        automated_test_results = repo.get_automated_test_results()

        for urn_id, req_data in all_requirements.items():
            # Get all svc UrnIds related to current requirement
            svcs_urn_ids: list[UrnId] = repo.get_svcs_for_req(urn_id)

            # Get svcs for current requirement
            svcs: list[SVCData] = [all_svcs[sid] for sid in svcs_urn_ids if sid in all_svcs]

            # Get all verification types for current req
            verifications_as_string = ", ".join(str(svc.verification.value) for svc in svcs)

            # get all implementations for current requirement
            impls: list = self._get_annotation_impls(repo=repo, urn_id=urn_id)

            # Get MVR IDs via SVCs
            mvr_ids: list[UrnId] = [mid for svc_uid in svcs_urn_ids for mid in repo.get_mvrs_for_svc(svc_uid)]

            # Get mvrs for current requirement if there are any (else [])
            mvrs: list[MVRData] = [all_mvrs[mvr_id] for mvr_id in mvr_ids if mvr_id in all_mvrs] if mvr_ids else []

            # generate templates for tests related to current requirement
            automated_test_results_for_req: list = self._get_annotated_automated_test_results_for_req(
                repo=repo, svcs_urn_ids=svcs_urn_ids, automated_test_results=automated_test_results
            )

            req_temp_data = {
                "id": urn_id.id,
                "categories": req_data.categories,
                "description": req_data.description,
                "rationale": req_data.rationale,
                "references": ", ".join(
                    f"{uid.urn}:{uid.id}"
                    for reference in req_data.references
                    for uid in sorted(reference.requirement_ids)
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
                "tests": automated_test_results_for_req,
                "mvrs": mvrs,
            }

            requirement_data[urn_id] = data_container

        return requirement_data

    def _get_annotated_automated_test_results_for_req(
        self,
        repo: RequirementsRepository,
        svcs_urn_ids: list[UrnId],
        automated_test_results: dict[UrnId, list],
    ) -> list:
        results = []
        annotations_tests = repo.get_annotations_tests()
        for svc_uid in svcs_urn_ids:
            if svc_uid in annotations_tests:
                annotations = annotations_tests[svc_uid]
                for test in annotations:
                    test_urn_id = UrnId(urn=svc_uid.urn, id=test.fully_qualified_name)
                    if test_urn_id in automated_test_results:
                        test_results = automated_test_results[test_urn_id]
                        results_as_string = ", ".join(str(r.status.value) for r in test_results)
                    else:
                        results_as_string = str(TEST_RUN_STATUS.MISSING.value)
                    annot_test = {
                        "svc_id": svc_uid.id,
                        "element_kind": test.element_kind,
                        "fqn": test.fully_qualified_name,
                        "test_result": results_as_string,
                    }
                    results.append(annot_test)

        return results

    def _get_annotation_impls(self, repo: RequirementsRepository, urn_id: UrnId):
        impls_list = []
        impls_for_urn: list[AnnotationData] = repo.get_annotations_impls_for_req(urn_id)
        if impls_for_urn:
            for impl in impls_for_urn:
                impl_template = {"element_kind": impl.element_kind, "fqn": impl.fully_qualified_name}
                impls_list.append(impl_template)

        return impls_list
