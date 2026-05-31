# Copyright © LFV


from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.services.statistics_service import EXPECTS_MVRS
from reqstool.storage.pipeline import build_database
from reqstool.storage.requirements_repository import RequirementsRepository


class ValidateCommand:
    """Validate spec completeness: every requirement has ≥1 SVC; every manual SVC has an MVR.

    Also surfaces referential-integrity errors from SemanticValidator (broken SVC/MVR/annotation
    references). Referential errors are always fatal; coverage gaps are warnings by default and
    become errors with --strict.
    """

    def __init__(self, location: LocationInterface, strict: bool = False):
        self.__initial_location = location
        self.__strict = strict
        self.result, self.exit_code = self.__run()

    def __run(self) -> tuple[str, int]:
        holder = ValidationErrorHolder()
        with build_database(
            location=self.__initial_location,
            semantic_validator=SemanticValidator(validation_error_holder=holder),
        ) as (db, _):
            repo = RequirementsRepository(db)
            initial_urn = repo.get_initial_urn()
            ref_errors = [e.msg.strip() for e in holder.get_errors()]
            coverage_warnings = self._check_coverage(repo)

        lines = []
        lines.append(f"Validating reqstool setup · {initial_urn}\n")

        if ref_errors:
            lines.append("")
            for msg in ref_errors:
                lines.append(f"✗ {msg}")

        if coverage_warnings:
            lines.append("")
            for msg in coverage_warnings:
                lines.append(f"⚠ {msg}")

        n_errors = len(ref_errors)
        n_warnings = len(coverage_warnings)

        if not ref_errors and not coverage_warnings:
            lines.append("\n✓ All checks passed\n")
            exit_code = 0
        else:
            summary_parts = []
            if n_errors:
                summary_parts.append(f"{n_errors} error{'s' if n_errors != 1 else ''}")
            if n_warnings:
                summary_parts.append(f"{n_warnings} warning{'s' if n_warnings != 1 else ''}")
            lines.append("\n" + " · ".join(summary_parts))
            if not ref_errors and n_warnings and not self.__strict:
                lines.append("  (use --strict to treat warnings as errors)\n")
            else:
                lines.append("\n")
            exit_code = 1 if (ref_errors or (coverage_warnings and self.__strict)) else 0

        return "\n".join(lines), exit_code

    def _check_coverage(self, repo: RequirementsRepository) -> list[str]:
        warnings = []
        all_reqs = repo.get_all_requirements()
        all_svcs = repo.get_all_svcs()

        for urn_id in all_reqs:
            svc_ids = repo.get_svcs_for_req(urn_id)
            if not svc_ids:
                warnings.append(f"{urn_id}    no SVC defined")

        for svc_uid, svc in all_svcs.items():
            if svc.verification in EXPECTS_MVRS:
                mvr_ids = repo.get_mvrs_for_svc(svc_uid)
                if not mvr_ids:
                    warnings.append(f"{svc_uid}    {svc.verification.value} — no MVR defined")

        return warnings
