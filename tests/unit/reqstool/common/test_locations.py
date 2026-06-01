# Copyright © LFV

import pytest

from reqstool.locations.git_location import GitLocation
from reqstool.locations.local_location import LocalLocation
from reqstool.locations.maven_location import MavenLocation


@pytest.fixture
def git_location_data():
    return GitLocation(
        token="GITLAB_TOKEN",
        ref="main",
        url="https://gitlab.example.com",
        path="some/path",
    )


@pytest.fixture
def local_location_data():
    return LocalLocation(path="/some/path")


@pytest.fixture
def maven_location_data():
    return MavenLocation(
        token="MAVEN_TOKEN",
        url="https://repo1.maven.org/maven2",
        group_id="com.example",
        artifact_id="artifactexample",
        version="0.0.1",
        classifier="classifierexample",
    )


def test_git_location_data(git_location_data):
    assert git_location_data.token == "GITLAB_TOKEN"
    assert git_location_data.ref == "main"
    assert git_location_data.url == "https://gitlab.example.com"
    assert git_location_data.path == "some/path"


def test_local_location_data(local_location_data):
    assert local_location_data.path == "/some/path"


def test_maven_location_data(maven_location_data):
    assert maven_location_data.token == "MAVEN_TOKEN"
    assert maven_location_data.url == "https://repo1.maven.org/maven2"
    assert maven_location_data.group_id == "com.example"
    assert maven_location_data.artifact_id == "artifactexample"
    assert maven_location_data.version == "0.0.1"
    assert maven_location_data.classifier == "classifierexample"
