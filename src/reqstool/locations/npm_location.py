# Copyright © LFV

import logging
import os
import tarfile
from typing import Optional
from urllib.parse import quote, urlparse

import requests

from reqstool.common.exceptions import ArtifactDownloadError, ArtifactExtractionError
from reqstool.common.utils import Utils
from reqstool.locations.location import LocationInterface


class NpmLocation(LocationInterface):
    url: str = "https://registry.npmjs.org"
    package: str
    version: str
    env_token: Optional[str] = None

    def _make_available_on_localdisk(self, dst_path: str):
        token = os.getenv(self.env_token) if self.env_token else None

        try:
            tarball_url = self._get_tarball_url(token)
            logging.debug(f"Downloading npm package {self.package}@{self.version} from {tarball_url} to {dst_path}")

            # Only forward the Bearer token if the tarball is served from the same host as the registry
            registry_host = urlparse(self.url).netloc
            tarball_host = urlparse(tarball_url).netloc
            tarball_token = token if tarball_host == registry_host else None
            if token and tarball_token is None:
                logging.warning(
                    f"npm tarball host ({tarball_host}) differs from registry host ({registry_host}); "
                    "not forwarding auth token to prevent credential leakage"
                )

            downloaded_file = Utils.download_file(url=tarball_url, dst_path=dst_path, token=tarball_token)
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
        # URL-encode the package name: keep @ (valid in path), encode / (scope separator)
        encoded_pkg = quote(self.package, safe="@")
        metadata_url = f"{registry}/{encoded_pkg}/{self.version}"

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
