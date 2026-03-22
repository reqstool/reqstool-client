# Copyright © LFV

from typing import Callable, Dict, Optional, Set, Type, TypeVar

from reqstool.common.models.urn_id import UrnId
from reqstool.common.utils import Utils
from reqstool.filters.id_filters import IDFilters

F = TypeVar("F", bound=IDFilters)


def parse_filters(
    data: dict,
    ids_key: str,
    filter_cls: Type[F],
    validate_fn: Callable[[dict], None],
) -> Dict[str, F]:
    """Parse filter entries from raw YAML data into a dict of filter objects.

    This utility extracts the duplicated filter-parsing logic that was previously
    present in both RequirementsModelGenerator and SVCsModelGenerator.

    Args:
        data: Raw YAML data dict loaded from requirements.yml or svcs.yml.
        ids_key: The key used for explicit ID filters, either ``"requirement_ids"``
            or ``"svc_ids"``.
        filter_cls: The filter dataclass to instantiate, either
            :class:`~reqstool.filters.requirements_filters.RequirementFilter` or
            :class:`~reqstool.filters.svcs_filters.SVCFilter`.
        validate_fn: A callable that performs semantic validation on ``data`` (e.g.
            checks that includes/excludes are mutually exclusive). Called once before
            any parsing begins.

    Returns:
        A dict mapping URN strings to filter instances. Returns an empty dict when
        ``data`` contains no ``"filters"`` section.
    """
    r_filters: Dict[str, F] = {}

    validate_fn(data)

    if "filters" not in data:
        return r_filters

    for urn in data["filters"].keys():
        urn_filter = data["filters"][urn]

        urn_ids_imports: Optional[Set[UrnId]] = None
        urn_ids_excludes: Optional[Set[UrnId]] = None
        custom_includes = None
        custom_exclude = None

        if ids_key in urn_filter:
            if "includes" in urn_filter[ids_key]:
                filtered_ids = Utils.check_ids_to_filter(current_urn=urn, ids=urn_filter[ids_key]["includes"])
                ids_includes = list(filtered_ids)
                urn_ids_imports = set(Utils.convert_ids_to_urn_id(urn=urn, ids=ids_includes))

            if "excludes" in urn_filter[ids_key]:
                filtered_ids = Utils.check_ids_to_filter(current_urn=urn, ids=urn_filter[ids_key]["excludes"])
                ids_excludes = list(filtered_ids)
                urn_ids_excludes = set(Utils.convert_ids_to_urn_id(urn=urn, ids=ids_excludes))

        if "custom" in urn_filter:
            if "includes" in urn_filter["custom"]:
                custom_includes = urn_filter["custom"]["includes"]

            if "excludes" in urn_filter["custom"]:
                custom_exclude = urn_filter["custom"]["excludes"]

        r_filters[urn] = filter_cls(
            urn_ids_imports=urn_ids_imports,
            urn_ids_excludes=urn_ids_excludes,
            custom_imports=custom_includes,
            custom_exclude=custom_exclude,
        )

    return r_filters
