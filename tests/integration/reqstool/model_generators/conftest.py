# Copyright © reqstool

import os

import pytest

from integration.reqstool.model_generators._regression_shared import _GITHUB_TOKEN_ENV
from reqstool.common.utils import TempDirectoryManager

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv(_GITHUB_TOKEN_ENV, "").strip(),
        reason=f"Test needs {_GITHUB_TOKEN_ENV}",
    ),
]


@pytest.fixture(scope="module")
def shared_tmpdir():
    """Module-scoped TempDirectoryManager.

    Sharing one manager across all tests in a module means repeated GitLocation
    clones of the same URL reuse the existing checkout instead of re-cloning.
    """
    mgr = TempDirectoryManager()
    yield mgr
    mgr.cleanup()
