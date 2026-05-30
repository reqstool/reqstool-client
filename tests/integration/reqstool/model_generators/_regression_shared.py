# Copyright © reqstool
# Shared constants for regression-monorepo integration tests.

_REGRESSION_REPO_URL = "https://github.com/reqstool/reqstool-regression.git"
# Ref is intentionally 'main' (always latest regression data). Note: after a plain clone,
# 'main' resolves via the origin/main remote-tracking fallback in GitLocation._resolve_ref.
# To pin CI to a known-good state, replace "main" with a tag or commit SHA, e.g.:
#   _REGRESSION_REPO_REF = "v1.0.0"   # resolves directly (no fallback needed)
#   _REGRESSION_REPO_REF = "abc1234"  # resolves directly as commit SHA
_REGRESSION_REPO_REF = "main"
_GITHUB_TOKEN_ENV = "GITHUB_TOKEN"

# Single source of truth for ecosystem names.
# Both ECOSYSTEM_PATHS (for entry-point tests) and ECOSYSTEM_URNS (for structural tests)
# are derived here so adding a new ecosystem requires one change only.
_ECOSYSTEM_NAMES = ["python", "java", "typescript"]
ECOSYSTEM_PATHS = [f"fixtures/ecosystems/{name}" for name in _ECOSYSTEM_NAMES]
ECOSYSTEM_URNS = [f"regression-{name}" for name in _ECOSYSTEM_NAMES]
