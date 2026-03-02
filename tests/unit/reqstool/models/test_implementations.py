# Copyright © LFV

import pytest

from reqstool.locations.git_location import GitLocation
from reqstool.locations.local_location import LocalLocation
from reqstool.locations.maven_location import MavenLocation
from reqstool.models.implementations import GitImplData, LocalImplData, MavenImplData


@pytest.fixture
def git_impl_data() -> GitImplData:
    return GitImplData(
        parent=None,
        _current_unresolved=GitLocation(
            env_token="GITLAB_TOKEN",
            branch="main",
            url="https://github.com/reqstool/reqstool-client",
            path="/examples/README.adoc",
        ),
    )


@pytest.fixture
def local_impl_data() -> LocalImplData:
    return LocalImplData(parent=None, _current_unresolved=LocalLocation(path="some/path"))


@pytest.fixture
def maven_impl_data() -> MavenImplData:
    return MavenImplData(
        parent=None,
        _current_unresolved=MavenLocation(
            env_token="MAVEN_TOKEN",
            url="https://repo1.maven.org/maven2",
            group_id="com.example",
            artifact_id="artifactexample",
            version="0.0.1",
            classifier="someclassifier",
        ),
    )


@pytest.fixture
def implementations_data(maven_impl_data):
    return [maven_impl_data, maven_impl_data]


def test_git_impl_data(git_impl_data):
    assert git_impl_data.parent is None
    assert git_impl_data.current.env_token == "GITLAB_TOKEN"
    assert git_impl_data.current.branch == "main"
    assert git_impl_data.current.url == "https://github.com/reqstool/reqstool-client"
    assert git_impl_data.current.path == "/examples/README.adoc"


def test_local_impl_data(local_impl_data):
    assert local_impl_data.parent is None
    assert local_impl_data.current.path == "some/path"


def test_maven_impl_data(maven_impl_data):
    assert maven_impl_data.parent is None
    assert maven_impl_data.current.env_token == "MAVEN_TOKEN"
    assert maven_impl_data.current.url == "https://repo1.maven.org/maven2"
    assert maven_impl_data.current.group_id == "com.example"
    assert maven_impl_data.current.artifact_id == "artifactexample"
    assert maven_impl_data.current.version == "0.0.1"
    assert maven_impl_data.current.classifier == "someclassifier"


def test_implementations_data(implementations_data):
    assert len(implementations_data) == 2
