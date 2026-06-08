# Copyright © LFV

from enum import Enum, unique

from reqstool_python_decorators.decorators.decorators import Requirements


@Requirements("REPORT_0004")
@unique
class SortByOptions(Enum):
    ID = "id"
    SIGNIFICANCE = "significance"
    REVISION = "revision"
