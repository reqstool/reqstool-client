# Copyright © LFV

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from reqstool.common.exceptions import GitRefNotFoundError
from reqstool.locations.git_location import GitLocation
from reqstool_python_decorators.decorators.decorators import SVCs


def test_git_location():
    PATH = "/tmp/somepath"

    git_location = GitLocation(
        token="GITLAB_TOKEN",
        url="https://git.example.com/example/repo.git",
        ref="main",
        path=PATH,
    )

    assert git_location.token.get_secret_value() == "GITLAB_TOKEN"
    assert git_location.url == "https://git.example.com/example/repo.git"
    assert git_location.ref == "main"
    assert git_location.path == PATH

    git_location = GitLocation(
        token="CI_TOKEN",
        url="https://git.example.com/repo.git",
        ref="v1.2.0",
        path=PATH,
    )

    assert git_location.token.get_secret_value() == "CI_TOKEN"
    assert git_location.url == "https://git.example.com/repo.git"
    assert git_location.ref == "v1.2.0"
    assert git_location.path == PATH


def test_git_location_path_defaults_to_empty_string():
    git_location = GitLocation(
        url="https://git.example.com/repo.git",
        ref="main",
    )
    assert git_location.path == ""


def test_git_location_explicit_path_still_works():
    git_location = GitLocation(
        url="https://git.example.com/repo.git",
        ref="main",
        path="docs/reqstool",
    )
    assert git_location.path == "docs/reqstool"


def test_git_location_token_defaults_to_none():
    git_location = GitLocation(
        url="https://git.example.com/repo.git",
        ref="main",
        path="/tmp/somepath",
    )
    assert git_location.token is None


@pytest.mark.parametrize(
    "ref",
    ["main", "v1.2.0", "feature/my-feature", "abc1234def5678", "release_1.0", "some.branch"],
)
def test_git_location_valid_ref_accepted(ref):
    git_location = GitLocation(url="https://git.example.com/repo.git", ref=ref)
    assert git_location.ref == ref


@pytest.mark.parametrize(
    "ref",
    [
        "my..ref",  # double-dot (git range syntax)
        "@{upstream}",  # git reflog syntax
        "ref~1",  # relative ref
        "ref^",  # parent syntax
        "ref:path",  # colon (git tree-ish)
        "ref name",  # space
        ".hidden",  # starts with dot
        "-branch",  # starts with dash
        "ref\x00",  # null byte
    ],
)
def test_git_location_invalid_ref_rejected(ref):
    with pytest.raises(ValidationError):
        GitLocation(url="https://git.example.com/repo.git", ref=ref)


def test_git_location_tmpdir_key_includes_ref():
    loc = GitLocation(url="https://git.example.com/repo.git", ref="v1.0.0")
    assert "v1.0.0" in loc.tmpdir_key()


def _mock_repo(tmp_path):
    """A cloned-repo mock whose ref resolution and checkout calls are observable."""
    mock_repo = MagicMock()
    mock_repo.workdir = str(tmp_path)
    return mock_repo


@SVCs("SVC_SOURCE_0004")
@pytest.mark.parametrize("ref", ["v1.2.0", "main", "abc1234def5678"])
def test_git_location_make_available_resolves_ref(tmp_path, ref):
    """A tag, default branch, or SHA resolves directly via revparse_single and is checked out."""
    git_location = GitLocation(url="https://git.example.com/repo.git", ref=ref, path="")
    mock_repo = _mock_repo(tmp_path)

    with patch("reqstool.locations.git_location.clone_repository", return_value=mock_repo) as mock_clone:
        result = git_location._make_available_on_localdisk(str(tmp_path))

    mock_clone.assert_called_once()
    mock_repo.revparse_single.assert_called_once_with(ref)
    commit = mock_repo.revparse_single.return_value.peel.return_value
    mock_repo.checkout_tree.assert_called_once_with(commit)
    mock_repo.set_head.assert_called_once_with(commit.id)
    assert result == str(tmp_path)


def test_git_location_make_available_non_default_branch_uses_origin_fallback(tmp_path):
    """A non-default branch only exists as origin/<ref> after a plain clone, so the fallback is used."""
    git_location = GitLocation(url="https://git.example.com/repo.git", ref="feature/x", path="")
    mock_repo = _mock_repo(tmp_path)
    resolved = MagicMock()
    # First lookup (bare ref) misses; origin/<ref> resolves.
    mock_repo.revparse_single.side_effect = [KeyError("feature/x"), resolved]

    with patch("reqstool.locations.git_location.clone_repository", return_value=mock_repo):
        result = git_location._make_available_on_localdisk(str(tmp_path))

    assert [c.args[0] for c in mock_repo.revparse_single.call_args_list] == ["feature/x", "origin/feature/x"]
    mock_repo.checkout_tree.assert_called_once_with(resolved.peel.return_value)
    assert result == str(tmp_path)


def test_git_location_make_available_unresolvable_ref_raises(tmp_path):
    """An unresolvable ref (typo, deleted tag) raises a clear GitRefNotFoundError."""
    git_location = GitLocation(url="https://git.example.com/repo.git", ref="nope", path="")
    mock_repo = _mock_repo(tmp_path)
    mock_repo.revparse_single.side_effect = KeyError("nope")

    with patch("reqstool.locations.git_location.clone_repository", return_value=mock_repo):
        with pytest.raises(GitRefNotFoundError) as exc_info:
            git_location._make_available_on_localdisk(str(tmp_path))

    assert exc_info.value.ref == "nope"
    assert exc_info.value.url == "https://git.example.com/repo.git"


def test_git_location_make_available_git_error_treated_as_not_found(tmp_path):
    """A pygit2.GitError (e.g. malformed ref reaching revparse) is handled like a missing ref."""
    from pygit2 import GitError

    git_location = GitLocation(url="https://git.example.com/repo.git", ref="valid-ref", path="")
    mock_repo = _mock_repo(tmp_path)
    mock_repo.revparse_single.side_effect = GitError("internal error")

    with patch("reqstool.locations.git_location.clone_repository", return_value=mock_repo):
        with pytest.raises(GitRefNotFoundError):
            git_location._make_available_on_localdisk(str(tmp_path))


@SVCs("SVC_SOURCE_0008")
def test_git_location_make_available_with_token(tmp_path):
    git_location = GitLocation(url="https://git.example.com/repo.git", ref="main", path="", token="secret-token")
    mock_repo = _mock_repo(tmp_path)

    with patch("reqstool.locations.git_location.clone_repository", return_value=mock_repo) as mock_clone:
        git_location._make_available_on_localdisk(str(tmp_path))

    callbacks = mock_clone.call_args[1]["callbacks"]
    assert callbacks is not None
    assert callbacks.api_token == "secret-token"


def test_git_location_make_available_no_token_passes_no_callbacks(tmp_path):
    git_location = GitLocation(url="https://git.example.com/repo.git", ref="main", path="")
    mock_repo = _mock_repo(tmp_path)

    with patch("reqstool.locations.git_location.clone_repository", return_value=mock_repo) as mock_clone:
        git_location._make_available_on_localdisk(str(tmp_path))

    assert mock_clone.call_args[1]["callbacks"] is None


def test_git_location_token_not_in_repr():
    loc = GitLocation(url="https://git.example.com/repo.git", ref="main", token="super-secret")
    assert "super-secret" not in repr(loc)
