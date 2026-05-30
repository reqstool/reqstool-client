# Copyright © LFV

import logging
import os
import re
import tarfile
import tempfile
from importlib.metadata import version
from itertools import chain
from pathlib import Path
from typing import Dict, Iterable, List, Sequence
from zipfile import ZipFile

import expandvars
import requests
from packaging.version import InvalidVersion, Version as PkgVersion
from requests_file import FileAdapter

from reqstool.common.exceptions import EnvVarInterpolationError
from reqstool.common.models.urn_id import UrnId
from reqstool.models.raw_datasets import RawDataset
from reqstool.models.requirements import RequirementData
from reqstool.models.svcs import SVCData


class Utils:

    is_installed_package: bool = True

    # Only the braced ``${...}`` form is interpolated. The bare ``$VAR`` form is
    # intentionally left untouched: reqstool YAML files routinely contain a
    # ``# yaml-language-server: $schema=...`` directive (and regexes, prices,
    # etc.) where a stray ``$`` must not be treated as a variable reference.
    _ENV_VAR_PATTERN = re.compile(r"\$\{[^{}]*\}")

    @staticmethod
    def interpolate_env_vars(text: str, source: str | None = None) -> str:
        """Expand environment variables in raw YAML text before parsing.

        Uses POSIX shell parameter expansion (the ``envsubst`` standard),
        restricted to the braced form::

            ${VAR}            substitute the value of VAR
            ${VAR:-default}   use ``default`` when VAR is unset or empty
            ${VAR:?message}   fail with ``message`` when VAR is unset or empty
            ${VAR:+alt}       use ``alt`` when VAR is set

        A bare ``${VAR}`` whose variable is unset (and has no inline default)
        is a hard error: this keeps ingestion deterministic and catches
        misconfiguration in CI rather than silently producing empty values.

        Args:
            text: raw file contents to interpolate.
            source: optional file path/URI used in error messages.

        Raises:
            EnvVarInterpolationError: on an unset variable without a default or
                a malformed ``${...}`` expression.
        """

        def _expand(match: "re.Match[str]") -> str:
            try:
                return expandvars.expand(match.group(0), nounset=True)
            except expandvars.ExpandvarsException as e:
                raise EnvVarInterpolationError(str(e), source=source) from e

        return Utils._ENV_VAR_PATTERN.sub(_expand, text)

    @staticmethod
    def get_version() -> str:
        ver: str = f"{version('reqstool')}" if Utils.is_installed_package else "local-dev"

        return ver

    @staticmethod
    def extract_zip(zip_path: str, dst_path: str) -> str:
        with ZipFile(zip_path, "r") as zip_ref:
            top_level_dirs = {name.split("/")[0] for name in zip_ref.namelist() if "/" in name}
            if len(top_level_dirs) != 1:
                raise ValueError(f"ZIP artifact did not have exactly one top-level directory: {top_level_dirs}")
            zip_ref.extractall(path=dst_path)
        top_level_dir = os.path.join(dst_path, top_level_dirs.pop())
        logging.debug(f"Extracted {zip_path} to {top_level_dir}")
        return top_level_dir

    @staticmethod
    def extract_targz(targz_path: str, dst_path: str) -> str:
        with tarfile.open(targz_path, "r:gz") as tar_ref:
            top_level_dirs = {member.name.split("/")[0] for member in tar_ref.getmembers() if "/" in member.name}
            if len(top_level_dirs) != 1:
                raise ValueError(f"tar.gz artifact did not have exactly one top-level directory: {top_level_dirs}")
            tar_ref.extractall(path=dst_path, filter="data")
        top_level_dir = os.path.join(dst_path, top_level_dirs.pop())
        logging.debug(f"Extracted {targz_path} to {top_level_dir}")
        return top_level_dir

    @staticmethod
    def download_file(url, dst_path, token=None, **kwargs) -> Path:

        response = Utils.open_file_https_file(url, token=token, **kwargs)

        # Raise an error if the request was unsuccessful
        response.raise_for_status()

        fn: Path = os.path.abspath(Path(dst_path, os.path.basename(url)))
        with open(fn, "wb") as file:
            file.write(response.content)

        logging.debug(f"Downloaded {url} to {fn}")

        return fn

    @staticmethod
    def open_file_https_file(uri: str, token=None, **kwargs):
        user_agent = f"reqstool/{Utils.get_version()}"

        headers = {"User-Agent": user_agent}

        if token:
            # If the token exists, add it as a Bearer token in the Authorization header
            headers["Authorization"] = f"Bearer {token}"

        session = requests.Session()
        session.mount("file://", FileAdapter())

        if not (uri.startswith("https://")):
            path: Path = Path(uri)

            uri = "file://" + str(path.absolute())

        response = session.get(url=uri, headers=headers, allow_redirects=True, **kwargs)

        return response

    @staticmethod
    def get_matching_files(path: str, patterns: List[str]) -> List[Path]:
        matching_files = []

        for pattern in patterns:
            matching_files.extend(Path(path).rglob(pattern))

        return list(set(matching_files))  # Remove duplicates if patterns overlap

    @staticmethod
    def flatten_all_reqs(raw_datasets: Dict[str, RawDataset]) -> Dict[str, RequirementData]:
        """Returns a Dict of all filtered RequirementData of all imported models

        Args:
            models (Dict[str, RawDataset]): The models where filtered RequirementData should be extracted

        Returns:
            Dict[str, RequirementData]: All filtered RequirementData from models
        """
        all_reqs = {}
        for model_id, model_info in raw_datasets.items():
            for req_id, req_info in model_info.requirements_data.requirements.items():
                # unique_id = model_id + ":" + req_id
                if req_id not in all_reqs:
                    all_reqs[req_id] = req_info

        return all_reqs

    @staticmethod
    def flatten_all_svcs(raw_datasets: Dict[str, RawDataset]) -> Dict[str, SVCData]:
        """Returns a Dict of all filtered SVCData of all imported models

        Args:
            models (Dict[str, RawDataset]): The models where the filtered SVCData should be extracted

        Returns:
            Dict[str, SVCData]: All filtered SVCData from models
        """
        all_svcs = {}

        for model_id, model_info in raw_datasets.items():
            if model_info.svcs_data is not None:
                for svc_id, svc in model_info.svcs_data.cases.items():
                    if svc_id not in all_svcs:
                        all_svcs[svc_id] = svc

        return all_svcs

    @staticmethod
    def flatten_list(list_to_flatten: Iterable) -> List[any]:
        return list(chain.from_iterable(list_to_flatten))

    @staticmethod
    def string_contains_delimiter(string: str, delimiter: str) -> bool:
        return delimiter in string

    @staticmethod
    def get_after_colon_or_original(input_string):
        parts = input_string.rsplit(":", 1)  # Split only once from the right
        if len(parts) > 1:
            return parts[-1]
        return input_string

    @staticmethod
    def convert_ids_to_urn_id(urn: str, ids: Sequence[str]) -> List[UrnId]:
        ids_as_urn_ids = []

        for id in ids:
            urn_id = Utils.convert_id_to_urn_id(urn, id)

            ids_as_urn_ids.append(urn_id)

        return ids_as_urn_ids

    @staticmethod
    def convert_id_to_urn_id(urn: str, id: str) -> UrnId:
        if ":" in id:
            split = id.split(":")
            urn_id = UrnId(urn=split[0], id=split[1])
        else:
            # if no ":" in svc_id, append with specified urn
            urn_id = UrnId(urn=urn, id=id)

        return urn_id

    # Checks conditions for filtered ids and logs an error if they are not properly formatted
    @staticmethod
    def check_ids_to_filter(ids: Sequence[str], current_urn: str) -> Sequence[str]:
        checked_ids: List[str] = []
        for id in ids:
            if ":" in id:
                split = id.split(":")
                if split[0] != current_urn:
                    logging.error(
                        f"Id cannot contain a ':' and a reference to another urn. The {id} will be filtered out"
                    )
                else:
                    checked_ids.append(id)
            else:
                id_with_urn = current_urn + ":" + id
                checked_ids.append(id_with_urn)
        return checked_ids

    @staticmethod
    def parse_version(version_str: str, urn_id: UrnId) -> PkgVersion:
        try:
            return PkgVersion(version_str)
        except InvalidVersion as e:
            raise TypeError(f"Invalid version: {e} for: {urn_id}")


class TempDirectoryManager:
    """Instance-based temporary directory manager with guaranteed cleanup."""

    def __init__(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._count = 0

    def get_path(self) -> Path:
        return Path(self._tmpdir.name)

    def get_suffix_path(self, suffix: str) -> Path:
        new_path = Path(self._tmpdir.name) / str(self._count) / suffix
        root = Path(self._tmpdir.name).resolve()
        if not new_path.resolve().is_relative_to(root):
            raise ValueError(f"suffix {suffix!r} would escape the managed temp directory")
        new_path.mkdir(parents=True, exist_ok=True)
        self._count += 1
        return new_path

    def cleanup(self):
        self._tmpdir.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cleanup()
