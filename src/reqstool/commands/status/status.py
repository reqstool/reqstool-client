# Copyright © LFV


import json
import logging
import shutil
from enum import Enum
from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.table import Table, box
from rich.text import Text
from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.models.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.model_generators.testdata_model_generator import TestDataModelGenerator
from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import IMPLEMENTATION, NON_CODE_IMPLEMENTATIONS
from reqstool.models.svcs import SVCData
from reqstool.services.export_service import ExportService
from reqstool.services.statistics_service import (
    EXPECTS_MVRS,
    RequirementStatus,
    StatisticsService,
    TestStats,
    TotalStats,
)
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.pipeline import build_database
from reqstool.storage.requirements_repository import RequirementsRepository


_ORANGE = "dark_orange"
_DIM = "dim"
_MIN_CONSOLE_WIDTH = 80

# Labels shown in the Implementation cell for non-code requirement types.
_NON_CODE_LABELS: dict[IMPLEMENTATION, str] = {
    IMPLEMENTATION.NOT_APPLICABLE: "N/A",
    IMPLEMENTATION.CONFIGURATION: "configuration",
    IMPLEMENTATION.PLATFORM: "platform",
    IMPLEMENTATION.FRAMEWORK: "framework",
}
assert (
    set(_NON_CODE_LABELS) == NON_CODE_IMPLEMENTATIONS
), f"_NON_CODE_LABELS keys {set(_NON_CODE_LABELS)} must match NON_CODE_IMPLEMENTATIONS {NON_CODE_IMPLEMENTATIONS}"


class VerbosityLevel(Enum):
    COMPACT = "compact"
    NORMAL = "normal"
    VERBOSE = "verbose"
    EXTRA_VERBOSE = "extra-verbose"


def _make_console() -> Console:
    width = max(_MIN_CONSOLE_WIDTH, shutil.get_terminal_size((120, 24)).columns)
    return Console(highlight=False, force_terminal=True, color_system="standard", width=width)


def _render(*renderables) -> str:
    console = _make_console()
    with console.capture() as cap:
        for r in renderables:
            console.print(r)
    return cap.get()


@Requirements("REQ_027")
class StatusCommand:
    def __init__(
        self,
        location: LocationInterface,
        format: str = "console",
        verbosity: str = VerbosityLevel.NORMAL.value,
        incomplete_only: bool = False,
        req_ids: list[str] | None = None,
        svc_ids: list[str] | None = None,
        with_post_tests: list[str] | None = None,
    ):
        self.__initial_location: LocationInterface = location
        self.__format: str = format
        self.__verbosity: str = verbosity
        self.__incomplete_only: bool = incomplete_only
        self.__req_ids: list[str] | None = req_ids
        self.__svc_ids: list[str] | None = svc_ids
        self.__with_post_tests: list[str] | None = with_post_tests

        if self.__format == "json" and self.__verbosity != VerbosityLevel.NORMAL.value:
            logging.warning("--verbosity has no effect when --format json is used; ignoring")

        self.result = self.__status_result()

    def __status_result(self) -> tuple[str, int]:
        with build_database(
            location=self.__initial_location,
            semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
        ) as (db, _):
            repo = RequirementsRepository(db)
            if self.__with_post_tests:
                self.__inject_post_tests(db, repo.get_initial_urn(), self.__with_post_tests)
            stats_service = StatisticsService(repo, include_post_build=bool(self.__with_post_tests))

            if self.__format == "json":
                req_filter = None
                if self.__req_ids or self.__svc_ids:
                    initial_urn = repo.get_initial_urn()
                    export_service = ExportService(repo)
                    req_filter, _ = export_service.resolve_filter_scope(self.__req_ids, self.__svc_ids, initial_urn)
                status = json.dumps(_filtered_status_dict(stats_service, req_filter), indent=2)
            else:
                level = VerbosityLevel(self.__verbosity)
                match level:
                    case VerbosityLevel.COMPACT:
                        status = _status_compact(stats_service)
                    case VerbosityLevel.VERBOSE:
                        status = _status_verbose(stats_service, self.__incomplete_only)
                    case VerbosityLevel.EXTRA_VERBOSE:
                        status = _status_extra_verbose(stats_service, repo, self.__incomplete_only)
                    case _:  # NORMAL
                        status = _status_normal(stats_service, self.__incomplete_only)

            ts = stats_service.total_statistics
            return (
                status,
                ts.total_requirements - ts.completed_requirements,
            )

    @staticmethod
    def __inject_post_tests(db: RequirementsDatabase, initial_urn: str, paths: list[str]) -> None:
        resolved = [Path(p).resolve() for p in paths]
        missing = [p for p in resolved if not p.is_file()]
        if missing:
            raise FileNotFoundError(f"--with-post-tests: file(s) not found: {', '.join(str(p) for p in missing)}")
        generator = TestDataModelGenerator(test_result_files=resolved, urn=initial_urn)
        for urn_id, test_data in generator.model.tests.items():
            db.insert_test_result(urn_id.urn, test_data.fully_qualified_name, test_data.status)


def _filtered_status_dict(stats_service: StatisticsService, kept_req_ids: set | None) -> dict:
    full = stats_service.to_status_dict()
    if kept_req_ids is not None:
        kept_keys = {str(uid) for uid in kept_req_ids}
        full["requirements"] = {k: v for k, v in full["requirements"].items() if k in kept_keys}
    return full


def _status_verdict(incomplete_count: int) -> str:
    return "PASS" if incomplete_count == 0 else "FAIL"


def _build_sections(
    complete_items: list[str],
    incomplete_items: list[str],
    incomplete_only: bool,
) -> str:
    """Build the COMPLETE / INCOMPLETE section body, respecting --incomplete-only."""
    sections = []
    if not incomplete_only:
        if complete_items:
            sections.append(f"COMPLETE ({len(complete_items)})\n" + "\n".join(complete_items))
        else:
            sections.append("COMPLETE (0)")
    if incomplete_items:
        sections.append(f"INCOMPLETE ({len(incomplete_items)})\n" + "\n".join(incomplete_items))
    elif not incomplete_only:
        sections.append("INCOMPLETE (0)")
    return "\n\n".join(sections)


def _incomplete_reasons(status: RequirementStatus) -> str:
    reasons = []
    if status.implementation_type == IMPLEMENTATION.IN_CODE and status.implementations == 0:
        reasons.append("not implemented")
    if not status.automated_tests.not_applicable:
        if status.automated_tests.failed > 0:
            passed = status.automated_tests.passed
            total = status.automated_tests.total
            reasons.append(f"automated test failed ({passed}/{total} passed)")
        if status.automated_tests.missing > 0:
            reasons.append("automated test missing")
    if not status.manual_tests.not_applicable:
        if status.manual_tests.failed > 0:
            reasons.append("manual verification failed")
        if status.manual_tests.missing > 0:
            reasons.append("manual result missing")
    return " · ".join(reasons) if reasons else "incomplete"


def _status_compact(stats_service: StatisticsService) -> str:
    ts = stats_service.total_statistics
    urn = stats_service.initial_urn
    incomplete = ts.total_requirements - ts.completed_requirements
    return (
        f"{urn}: {ts.total_requirements} requirements · "
        f"{ts.completed_requirements} complete · "
        f"{incomplete} incomplete · {_status_verdict(incomplete)}\n"
    )


def _status_normal(stats_service: StatisticsService, incomplete_only: bool = False) -> str:
    ts = stats_service.total_statistics
    urn = stats_service.initial_urn
    incomplete_count = ts.total_requirements - ts.completed_requirements
    col_id, col_urn = 18, 10

    complete_lines = []
    incomplete_lines = []
    for req_uid, req_status in stats_service.requirement_statistics.items():
        id_str = f"{req_uid.id:<{col_id}}"
        urn_str = f"{req_uid.urn:<{col_urn}}"
        if req_status.completed:
            complete_lines.append(f"  {id_str}  {urn_str}")
        else:
            incomplete_lines.append(f"  {id_str}  {urn_str}  {_incomplete_reasons(req_status)}")

    body = _build_sections(complete_lines, incomplete_lines, incomplete_only)
    footer = (
        f"\n{ts.completed_requirements}/{ts.total_requirements} complete · "
        f"{incomplete_count} incomplete · {_status_verdict(incomplete_count)}\n"
    )
    return f"Requirements status · {urn}\n\n{body}{footer}"


def _status_verbose(stats_service: StatisticsService, incomplete_only: bool = False) -> str:
    ts = stats_service.total_statistics

    legend = Text("T = Total, ")
    legend.append("P = Passed", style="green")
    legend.append(", ")
    legend.append("F = Failed", style="red")
    legend.append(", ")
    legend.append("S = Skipped", style="yellow")
    legend.append(", ")
    legend.append("M = Missing", style=_ORANGE)

    table = Table(
        box=box.DOUBLE_EDGE,
        show_header=True,
        header_style="bold",
        show_lines=True,
        title=f"REQUIREMENTS: {ts.total_requirements}",
        title_style="bold",
        caption=legend,
    )
    table.add_column("URN", justify="center")
    table.add_column("ID", justify="left")
    table.add_column("Implementation", justify="center")
    table.add_column("Automated Tests", justify="center")
    table.add_column("Manual Tests", justify="center")

    for req, stats in stats_service.requirement_statistics.items():
        if incomplete_only and stats.completed:
            continue
        table.add_row(
            *_build_table(
                req_id=req.id,
                urn=req.urn,
                impls=stats.implementations,
                tests=stats.automated_tests,
                mvrs=stats.manual_tests,
                completed=stats.completed,
                implementation=stats.implementation_type,
            )
        )

    table.add_section()
    table.add_row(*_get_row_with_totals(stats_service))

    return _render(table)


def _status_extra_verbose(
    stats_service: StatisticsService, repo: RequirementsRepository, incomplete_only: bool = False
) -> str:
    ts = stats_service.total_statistics
    urn = stats_service.initial_urn
    incomplete_count = ts.total_requirements - ts.completed_requirements

    all_svcs = repo.get_all_svcs()
    all_mvrs = repo.get_all_mvrs()

    complete_lines = []
    incomplete_blocks = []
    for req_uid, req_status in stats_service.requirement_statistics.items():
        if req_status.completed:
            complete_lines.append(f"  ✓ {req_uid.id} · {req_uid.urn}")
        else:
            incomplete_blocks.append(_build_drill_down_block(req_uid, req_status, repo, all_svcs, all_mvrs))

    body = _build_sections(complete_lines, incomplete_blocks, incomplete_only)
    footer = (
        f"\n{ts.completed_requirements}/{ts.total_requirements} complete · "
        f"{incomplete_count} incomplete · {_status_verdict(incomplete_count)}\n"
    )
    return f"Requirements status · {urn}\n\n{body}{footer}"


def _build_drill_down_block(
    req_uid: UrnId,
    req_status: RequirementStatus,
    repo: RequirementsRepository,
    all_svcs: dict[UrnId, SVCData],
    all_mvrs: dict[UrnId, MVRData],
) -> str:
    lines = [f"✗ {req_uid.id} · {req_uid.urn} · {_incomplete_reasons(req_status)}"]

    impl_annotations = repo.get_annotations_impls_for_req(req_uid)
    if impl_annotations:
        for i, ann in enumerate(impl_annotations):
            prefix = "    implementation   " if i == 0 else "                     "
            lines.append(f"{prefix}{ann.fully_qualified_name}")
    else:
        lines.append("    implementation   (none)")

    for svc_uid in repo.get_svcs_for_req(req_uid):
        svc = all_svcs.get(svc_uid)
        if svc is None:
            continue
        lines.append(f"    {svc_uid.id:<16} {svc.verification.value}")
        if svc.verification in EXPECTS_MVRS:
            lines.extend(_render_mvrs(svc_uid, all_mvrs, repo))
        else:
            lines.extend(_render_test_results(svc_uid, repo))

    return "\n".join(lines)


def _render_mvrs(svc_uid: UrnId, all_mvrs: dict[UrnId, MVRData], repo: RequirementsRepository) -> list[str]:
    mvr_ids = repo.get_mvrs_for_svc(svc_uid)
    if not mvr_ids:
        return ["                     ⌀ no manual result"]
    lines = []
    for mvr_uid in mvr_ids:
        mvr = all_mvrs.get(mvr_uid)
        if mvr is None:
            continue
        icon = "✓" if mvr.passed else "✗"
        comment = f'  "{mvr.comment}"' if mvr.comment else ""
        lines.append(f"                     {icon} {mvr_uid.id}{comment}")
    return lines


def _render_test_results(svc_uid: UrnId, repo: RequirementsRepository) -> list[str]:
    test_results = repo.get_test_results_for_svc(svc_uid)
    if not test_results:
        return ["                     (no test results)"]
    icons = {"passed": "✓", "failed": "✗", "skipped": "~", "missing": "?"}
    lines = []
    for t in test_results:
        icon = icons.get(t.status.value, "?")
        name = t.fully_qualified_name.split(".")[-1] if t.fully_qualified_name else "(missing)"
        lines.append(f"                     {icon} {name}")
    return lines


# ---------------------------------------------------------------------------
# Table helpers — used by _status_verbose and existing tests
# ---------------------------------------------------------------------------


def _format_test_cell(stats: TestStats) -> Text:
    """Format a TestStats into a Rich Text object with colored counts."""
    if stats.not_applicable:
        return Text()

    def _slot(value: int, style: str) -> Text:
        t = Text()
        if value == 0:
            t.append(" -", style=_DIM)
        else:
            t.append(f"{value:>2}", style=style)
        return t

    cell = Text()
    cell.append_text(_slot(stats.total, "default"))
    cell.append(" ")
    cell.append_text(_slot(stats.passed, "green"))
    cell.append(" ")
    cell.append_text(_slot(stats.failed, "red"))
    cell.append(" ")
    cell.append_text(_slot(stats.skipped, "yellow"))
    cell.append(" ")
    cell.append_text(_slot(stats.missing, _ORANGE))
    return cell


def _build_table(
    req_id: str,
    urn: str,
    impls: int,
    tests: TestStats,
    mvrs: TestStats,
    completed: bool,
    implementation: IMPLEMENTATION,
) -> list:
    id_style = "green" if completed else "red"
    row = [
        Text(urn),
        Text(req_id, style=id_style),
    ]
    if implementation in _NON_CODE_LABELS:
        row.append(Text(_NON_CODE_LABELS[implementation], style="dim"))
    else:
        impl_style = "green" if impls > 0 else "red"
        row.append(Text(str(impls), style=impl_style))
    row.append(_format_test_cell(tests))
    row.append(_format_test_cell(mvrs))
    return row


def _get_row_with_totals(stats_service: StatisticsService) -> list:
    ts = stats_service.total_statistics
    total_automatic = ts.passed_automatic_tests + ts.failed_automatic_tests
    total_manual = ts.passed_manual_tests + ts.failed_manual_tests
    total_implementations = sum(
        stats.implementations
        for stats in stats_service.requirement_statistics.values()
        if stats.implementation_type not in _NON_CODE_LABELS
    )
    auto_stats = TestStats(
        total=total_automatic,
        passed=ts.passed_automatic_tests,
        failed=ts.failed_automatic_tests,
        skipped=ts.skipped_tests,
        missing=ts.missing_automated_tests,
    )
    manual_stats = TestStats(
        total=total_manual,
        passed=ts.passed_manual_tests,
        failed=ts.failed_manual_tests,
        skipped=0,
        missing=ts.missing_manual_tests,
    )
    return [
        Text("Total"),
        Text(""),
        Text(str(total_implementations)),
        _format_test_cell(auto_stats),
        _format_test_cell(manual_stats),
    ]


def _summarize_statistics(ts: TotalStats) -> str:
    CODE, NA, CONFIGURATION, PLATFORM, FRAMEWORK, IMPLEMENTATIONS = __colorize_headers()

    annotated_not_verified = ts.with_implementation - ts.code_completed
    missing_annotation = ts.code_reqs - ts.with_implementation

    # In Code group: total, verified, annotated-but-not-verified, missing annotation
    code_table = Table(box=box.DOUBLE_EDGE, show_header=True, title=CODE, title_justify="center")
    code_table.add_column("Total", justify="center")
    code_table.add_column("Verified", justify="center")
    code_table.add_column("Annotated, not verified", justify="center")
    code_table.add_column("Missing annotation", justify="center")
    code_table.add_row(
        str(ts.code_reqs) + __numbers_as_percentage(numerator=ts.code_reqs, denominator=ts.code_reqs),
        str(ts.code_completed) + __numbers_as_percentage(numerator=ts.code_completed, denominator=ts.code_reqs),
        str(annotated_not_verified)
        + __numbers_as_percentage(numerator=annotated_not_verified, denominator=ts.code_reqs),
        str(missing_annotation) + __numbers_as_percentage(numerator=missing_annotation, denominator=ts.code_reqs),
    )

    def _non_code_table(title: Text, total: int, completed: int, overall_total: int) -> Table:
        # "Total (% of all)" = share of all requirements; "Verified"/"Not Verified" = share of this type
        t = Table(box=box.DOUBLE_EDGE, show_header=True, title=title, title_justify="center")
        t.add_column("Total (% of all)", justify="center")
        t.add_column("Verified", justify="center")
        t.add_column("Not Verified", justify="center")
        t.add_row(
            str(total) + __numbers_as_percentage(numerator=total, denominator=overall_total),
            str(completed) + __numbers_as_percentage(numerator=completed, denominator=total),
            str(total - completed) + __numbers_as_percentage(numerator=(total - completed), denominator=total),
        )
        return t

    overall = ts.total_requirements
    na_table = _non_code_table(NA, ts.without_implementation_total, ts.without_implementation_completed, overall)
    config_table = _non_code_table(CONFIGURATION, ts.configuration_total, ts.configuration_completed, overall)
    platform_table = _non_code_table(PLATFORM, ts.platform_total, ts.platform_completed, overall)
    framework_table = _non_code_table(FRAMEWORK, ts.framework_total, ts.framework_completed, overall)

    tests_table = Table(
        box=box.DOUBLE_EDGE, show_header=True, title=f"Total Tests: {ts.total_tests}", title_style="white"
    )
    tests_table.add_column("Passed tests", justify="center")
    tests_table.add_column("Failed tests", justify="center")
    tests_table.add_column("Skipped tests", justify="center")
    tests_table.add_row(
        str(ts.passed_tests) + __numbers_as_percentage(numerator=ts.passed_tests, denominator=ts.total_tests),
        str(ts.failed_tests) + __numbers_as_percentage(numerator=ts.failed_tests, denominator=ts.total_tests),
        str(ts.skipped_tests) + __numbers_as_percentage(numerator=ts.skipped_tests, denominator=ts.total_tests),
    )

    svcs_table = Table(box=box.DOUBLE_EDGE, show_header=True, title=f"Total SVCs: {ts.total_svcs}", title_style="white")
    svcs_table.add_column("SVCs missing tests", justify="center")
    svcs_table.add_column("SVCs missing MVRs", justify="center")
    svcs_table.add_row(
        str(ts.missing_automated_tests)
        + __numbers_as_percentage(numerator=ts.missing_automated_tests, denominator=ts.total_svcs),
        str(ts.missing_manual_tests)
        + __numbers_as_percentage(numerator=ts.missing_manual_tests, denominator=ts.total_svcs),
    )

    impl_tables = [code_table, config_table, platform_table, framework_table, na_table]  # N/A intentionally last
    stacked_rendered = "".join(_render(t) for t in impl_tables)
    impl_console = _make_console()
    with impl_console.capture() as cap:
        impl_console.print(IMPLEMENTATIONS, justify="center")
    impl_header = cap.get()

    return "\n" + impl_header + stacked_rendered + _render(Columns([tests_table, svcs_table]))


def __numbers_as_percentage(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return ""
    percentage = (numerator / denominator) * 100
    percentage_as_string = " ({:.2f}%)".format(percentage)
    return percentage_as_string


def __colorize_headers() -> tuple[Text, Text, Text, Text, Text, Text]:
    return (
        Text("In Code", style="white"),
        Text("N/A", style="white"),
        Text("Configuration", style="white"),
        Text("Platform", style="white"),
        Text("Framework", style="white"),
        Text("IMPLEMENTATIONS", style="bold white"),
    )
