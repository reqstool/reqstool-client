# Copyright © LFV

from enum import Enum, unique


@unique
class SortByOptions(Enum):
    ID = "id"
    SIGNIFICANCE = "significance"
    REVISION = "revision"
