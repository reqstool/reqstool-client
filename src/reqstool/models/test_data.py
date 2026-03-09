# Copyright © LFV

from enum import Enum
from typing import Dict

from pydantic import BaseModel, ConfigDict, Field

from reqstool.common.models.urn_id import UrnId


class TEST_RUN_STATUS(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    MISSING = "missing"


class TestData(BaseModel):
    model_config = ConfigDict(frozen=True)

    fully_qualified_name: str
    status: TEST_RUN_STATUS


class TestsData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # key: urn + fqn
    tests: Dict[UrnId, TestData] = Field(default_factory=dict)
