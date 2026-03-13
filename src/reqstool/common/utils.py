# Copyright © LFV

import logging
import os
import tarfile
import tempfile
from importlib.metadata import version
from itertools import chain
from pathlib import Path
from typing import Dict, Iterable, List, Sequence
from zipfile import ZipFile

import requests
from packaging.version import InvalidVersion, Version as PkgVersion
from requests_file import FileAdapter

from reqstool.common.models.urn_id import UrnId
from reqstool.models.raw_datasets import RawDataset
from reqstool.models.requirements import VARIANTS, RequirementData
from reqstool.models.svcs import SVCData


class Utils:

    is_installed_package: bool = True

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
            if Utils.model_is_external(raw_datasets=model_info):
                continue
            if model_info.svcs_data is not None:
                for svc_id, svc in model_info.svcs_data.cases.items():
                    if svc_id not in all_svcs:
                        all_svcs[svc_id] = svc

        return all_svcs

    @staticmethod
    def flatten_list(list_to_flatten: Iterable) -> List[any]:
        return list(chain.from_iterable(list_to_flatten))

    @staticmethod
    def model_is_external(raw_datasets: RawDataset) -> bool:
        return raw_datasets.requirements_data.metadata.variant.value == VARIANTS.EXTERNAL.value

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


class TempDirectoryUtil:
    tmpdir: tempfile.TemporaryDirectory = None
    count: int = 0

    @staticmethod
    def _get_tmpdir() -> tempfile.TemporaryDirectory:
        if TempDirectoryUtil.tmpdir is None:
            TempDirectoryUtil.tmpdir = tempfile.TemporaryDirectory()
        return TempDirectoryUtil.tmpdir

    @staticmethod
    def get_path() -> Path:
        return Path(TempDirectoryUtil._get_tmpdir().name)

    @staticmethod
    def get_suffix_path(suffix: str) -> Path:
        new_path = Path(
            os.path.join(
                TempDirectoryUtil._get_tmpdir().name,
                str(TempDirectoryUtil.count),
                suffix,
            )
        )
        new_path.mkdir(parents=True, exist_ok=True)
        TempDirectoryUtil.count += 1

        return new_path
