# Copyright © reqstool
# Shared constants for regression-monorepo integration tests.

_REGRESSION_REPO_URL = "https://github.com/reqstool/reqstool-regression.git"
# Branch is intentionally 'main' (always latest regression data).
# For stronger CI stability, pin to a commit SHA when the regression repo cuts stable releases.
_REGRESSION_REPO_BRANCH = "main"
_GITHUB_TOKEN_ENV = "GITHUB_TOKEN"

# Single source of truth for ecosystem names.
# Both ECOSYSTEM_PATHS (for entry-point tests) and ECOSYSTEM_URNS (for structural tests)
# are derived here so adding a new ecosystem requires one change only.
_ECOSYSTEM_NAMES = ["python", "java", "typescript"]
ECOSYSTEM_PATHS = [f"fixtures/ecosystems/{name}" for name in _ECOSYSTEM_NAMES]
ECOSYSTEM_URNS = [f"regression-{name}" for name in _ECOSYSTEM_NAMES]
