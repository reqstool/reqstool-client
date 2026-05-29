# Copyright © LFV

from unittest.mock import MagicMock, patch

import pytest

from reqstool.common.exceptions import GitRefNotFoundError
from reqstool.locations.git_location import GitLocation


def test_git_location():
    PATH = "/tmp/somepath"

    git_location = GitLocation(
        env_token="GITLAB_TOKEN",
        url="https://git.example.com/example/repo.git",
        ref="main",
        path=PATH,
    )

    assert git_location.env_token == "GITLAB_TOKEN"
    assert git_location.url == "https://git.example.com/example/repo.git"
    assert git_location.ref == "main"
    assert git_location.path == PATH

    git_location = GitLocation(
        env_token="CI_TOKEN",
        url="https://git.example.com/repo.git",
        ref="v1.2.0",
        path=PATH,
    )

    assert git_location.env_token == "CI_TOKEN"
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


def test_git_location_env_token_defaults_to_none():
    git_location = GitLocation(
        url="https://git.example.com/repo.git",
        ref="main",
        path="/tmp/somepath",
    )
    assert git_location.env_token is None


def _mock_repo(tmp_path):
    """A cloned-repo mock whose ref resolution and checkout calls are observable."""
    mock_repo = MagicMock()
    mock_repo.workdir = str(tmp_path)
    return mock_repo


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
