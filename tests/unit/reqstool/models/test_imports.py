# Copyright © LFV

import pytest

from reqstool.locations.git_location import GitLocation
from reqstool.locations.local_location import LocalLocation
from reqstool.locations.maven_location import MavenLocation
from reqstool.models import imports


@pytest.fixture
def git_import_data():
    return imports.GitImportData(
        parent=None,
        current_unresolved=GitLocation(
            env_token="GITLAB_TOKEN",
            branch="main",
            url="https://gitlab.example.com",
            path="git/some/path",
        ),
    )


@pytest.fixture
def local_import_data():
    return imports.LocalImportData(parent=None, current_unresolved=LocalLocation(path="local/some/path"))


@pytest.fixture
def maven_import_data():
    return imports.MavenImportData(
        parent=None,
        current_unresolved=MavenLocation(
            env_token="MAVEN_TOKEN",
            url="https://repo1.maven.org/maven2",
            group_id="com.example",
            artifact_id="artifactexample",
            version="0.0.1",
            classifier="classifierexample",
        ),
    )


def test_git_import_data(git_import_data):
    assert git_import_data.parent is None
    assert git_import_data.current.env_token == "GITLAB_TOKEN"
    assert git_import_data.current.branch == "main"
    assert git_import_data.current.url == "https://gitlab.example.com"
    assert git_import_data.current.path == "git/some/path"


def test_local_system_data(local_import_data):
    assert local_import_data.parent is None
    assert local_import_data.current.path == "local/some/path"


def test_maven_system_data(maven_import_data):
    assert maven_import_data.parent is None
    assert maven_import_data.current.env_token == "MAVEN_TOKEN"
    assert maven_import_data.current.url == "https://repo1.maven.org/maven2"
    assert maven_import_data.current.group_id == "com.example"
    assert maven_import_data.current.artifact_id == "artifactexample"
    assert maven_import_data.current.version == "0.0.1"
    assert maven_import_data.current.artifact_id == "artifactexample"
    assert maven_import_data.current.classifier == "classifierexample"
