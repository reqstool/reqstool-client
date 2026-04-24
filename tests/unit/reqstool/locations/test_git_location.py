# Copyright © LFV

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
