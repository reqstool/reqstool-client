# Copyright © LFV

import logging
import os
import tarfile
from typing import Optional

import requests

from reqstool.common.exceptions import ArtifactDownloadError, ArtifactExtractionError
from reqstool.common.utils import Utils
from reqstool.locations.location import LocationInterface


class NpmLocation(LocationInterface):
    """Download a reqstool dataset package from any npm-compatible registry.

    The package is expected to be a standard npm tarball whose top-level
    directory is ``package/`` (the npm convention).  The ``-reqstool`` naming
    suffix is a convention, not enforced here.
    """

    url: str = "https://registry.npmjs.org"
    package: str
    version: str
    env_token: Optional[str] = None

    def _make_available_on_localdisk(self, dst_path: str):
        token = os.getenv(self.env_token) if self.env_token else None

        try:
            tarball_url = self._get_tarball_url(token)
            logging.debug(f"Downloading npm package {self.package}@{self.version} from {tarball_url} to {dst_path}")
            downloaded_file = Utils.download_file(url=tarball_url, dst_path=dst_path, token=token)
            logging.debug(f"Extracting {downloaded_file} to {dst_path}")
            return Utils.extract_targz(str(downloaded_file), dst_path)
        except (ValueError, tarfile.TarError) as e:
            raise ArtifactExtractionError(str(e)) from e
        except ArtifactDownloadError:
            raise
        except Exception as e:
            raise ArtifactDownloadError(
                f"Error downloading npm package {self.package}@{self.version} from {self.url}"
                f"{' with token' if token else ''}: {e}"
            ) from e

    def _get_tarball_url(self, token: Optional[str]) -> str:
        """Fetch package metadata from the registry and return the tarball URL."""
        registry = self.url.rstrip("/")
        metadata_url = f"{registry}/{self.package}/{self.version}"

        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.get(metadata_url, headers=headers)
        response.raise_for_status()

        tarball_url = response.json().get("dist", {}).get("tarball")
        if not tarball_url:
            raise ArtifactDownloadError(
                f"npm registry response for {self.package}@{self.version} did not include dist.tarball"
            )
        return tarball_url
