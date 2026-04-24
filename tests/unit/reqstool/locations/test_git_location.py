# Copyright © LFV

from unittest.mock import MagicMock, patch

from reqstool.locations.git_location import GitLocation


def test_git_location(resource_funcname_rootdir_w_path):
    PATH = "/tmp/somepath"

    git_location = GitLocation(
        env_token="GITLAB_TOKEN",
        url="https://git.example.com/example/repo.git",
        branch="main",
        path=PATH,
    )

    assert git_location.env_token == "GITLAB_TOKEN"
    assert git_location.url == "https://git.example.com/example/repo.git"
    assert git_location.branch == "main"
    assert git_location.path == PATH

    git_location = GitLocation(
        env_token="CI_TOKEN",
        url="https://git.example.com/repo.git",
        branch="test",
        path=PATH,
    )

    assert git_location.env_token == "CI_TOKEN"
    assert git_location.url == "https://git.example.com/repo.git"
    assert git_location.branch == "test"
    assert git_location.path == PATH


def test_git_location_path_defaults_to_empty_string():
    git_location = GitLocation(
        url="https://git.example.com/repo.git",
        branch="main",
    )
    assert git_location.path == ""


def test_git_location_explicit_path_still_works():
    git_location = GitLocation(
        url="https://git.example.com/repo.git",
        branch="main",
        path="docs/reqstool",
    )
    assert git_location.path == "docs/reqstool"


def test_git_location_env_token_defaults_to_none():
    git_location = GitLocation(
        url="https://git.example.com/repo.git",
        branch="main",
        path="/tmp/somepath",
    )
    assert git_location.env_token is None


def test_git_location_make_available_no_env_token(tmp_path):
    git_location = GitLocation(url="https://git.example.com/repo.git", branch="main", path="")
    mock_repo = MagicMock()
    mock_repo.workdir = str(tmp_path)
    with patch("reqstool.locations.git_location.clone_repository", return_value=mock_repo) as mock_clone:
        result = git_location._make_available_on_localdisk(str(tmp_path))
    mock_clone.assert_called_once()
    assert result == str(tmp_path)
