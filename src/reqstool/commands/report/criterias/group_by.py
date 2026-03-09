# Copyright © LFV

from abc import ABC
from collections import defaultdict
from enum import Enum
from operator import attrgetter
from types import MappingProxyType
from typing import Callable, Dict, Iterator, List, Tuple

from pydantic import BaseModel, ConfigDict, Field

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.commands.report.criterias.sort_by import SortByOptions
from reqstool.common.models.urn_id import UrnId
from reqstool.models.combined_indexed_dataset import CombinedIndexedDataset
from reqstool.models.requirements import RequirementData


class GroupbyOptions(Enum):
    INITIAL_IMPORTS = "initial/imports"
    CATEGORY = "category"


@Requirements("REQ_033")
class GroupByOrganizor(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    cid: CombinedIndexedDataset
    group_by: GroupbyOptions
    sort_by: List[SortByOptions]

    grouped_requirements: Dict[str, List[UrnId]] = Field(init=False, default_factory=lambda: defaultdict(list))

    def model_post_init(self, __context):
        self._group()
        # make immutable
        self.grouped_requirements = MappingProxyType(dict(self.grouped_requirements))
        self._sort()

    def __iter__(self) -> Iterator[Tuple[str, List[UrnId]]]:
        return iter(self.grouped_requirements.items())

    def _add_req_to_group(self, group: str, urn_id: UrnId):
        self.grouped_requirements[group].append(urn_id)

    @Requirements("REQ_034")
    def _sort(self):
        if len(self.sort_by) == 0:
            return

        for group, urn_ids in self.grouped_requirements.items():
            urn_ids.sort(
                key=lambda urn_id: attrgetter(*[sort_option.value for sort_option in self.sort_by])(
                    self.cid.requirements[urn_id]
                )
            )

    def _group(self):

        for urn_id, req_data in self.cid.requirements.items():
            group = group_by_functions[self.group_by](req_data=req_data, cid=self.cid)

            self._add_req_to_group(group=group, urn_id=urn_id)


# Define the Callable interface with type annotations
GroupByFunction = Callable[[RequirementData, CombinedIndexedDataset], str]

# Define lambda functions for grouping
group_by_category: GroupByFunction = lambda req_data, cid: (
    req_data.categories[0].value if req_data.categories and len(req_data.categories) > 0 else "No Category"
)

group_by_initial_imported: GroupByFunction = lambda req_data, cid: (
    f"Initial URN ({cid.initial_model_urn})" if req_data.id.urn == cid.initial_model_urn else "Imported"
)

# Create a dictionary to map operation names to lambda functions
group_by_functions = {
    GroupbyOptions.CATEGORY: group_by_category,
    GroupbyOptions.INITIAL_IMPORTS: group_by_initial_imported,
}
