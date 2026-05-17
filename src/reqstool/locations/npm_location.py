# Copyright © LFV

import logging
import os
import tarfile
from typing import Optional
from urllib.parse import quote, urlparse

import requests
from pydantic import field_validator

from reqstool.common.exceptions import ArtifactDownloadError, ArtifactExtractionError
from reqstool.common.utils import Utils
from reqstool.locations.location import LocationInterface

_METADATA_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_REQUEST_TIMEOUT = 30  # seconds


class NpmLocation(LocationInterface):
    url: str = "https://registry.npmjs.org"
    package: str
    version: str
    env_token: Optional[str] = None

    @field_validator("url")
    @classmethod
    def url_must_be_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError(f"NpmLocation url must use https, got: {v!r}")
        return v

    def _make_available_on_localdisk(self, dst_path: str):
        """Resolve token → fetch tarball URL → SSRF check → download → extract."""
        token = os.getenv(self.env_token) if self.env_token else None

        try:
            tarball_url = self._get_tarball_url(token)
            logging.debug(f"Downloading npm package {self.package}@{self.version} from {tarball_url} to {dst_path}")

            registry_host = urlparse(self.url).netloc
            parsed_tarball = urlparse(tarball_url)
            if parsed_tarball.scheme != "https" or parsed_tarball.netloc != registry_host:
                raise ArtifactDownloadError(
                    f"Tarball URL {tarball_url!r} does not match registry host {registry_host!r}; "
                    "refusing download to prevent SSRF"
                )

            # allow_redirects=True is intentional: registries may redirect tarballs to CDN.
            # Cross-host redirect SSRF is an accepted risk; auth headers are stripped by
            # requests on cross-host redirects.
            downloaded_file = Utils.download_file(url=tarball_url, dst_path=dst_path, token=token)
        except ArtifactDownloadError:
            raise
        except Exception as e:
            raise ArtifactDownloadError(
                f"Error downloading npm package {self.package}@{self.version} from {self.url}"
                f"{' (authenticated)' if token else ''}: {type(e).__name__}"
            ) from e

        try:
            logging.debug(f"Extracting {downloaded_file} to {dst_path}")
            return Utils.extract_targz(str(downloaded_file), dst_path)
        except (ValueError, tarfile.TarError) as e:
            raise ArtifactExtractionError(str(e)) from e

    def _get_tarball_url(self, token: Optional[str]) -> str:
        """Fetch package metadata from the registry and return the tarball URL."""
        registry = self.url.rstrip("/")
        # Keep @ literal for scoped packages; encode / (scope separator) and version path chars
        encoded_pkg = quote(self.package, safe="@")
        encoded_version = quote(self.version, safe="")
        metadata_url = f"{registry}/{encoded_pkg}/{encoded_version}"

        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # allow_redirects=True is intentional; redirect-based SSRF is an accepted risk.
        response = requests.get(metadata_url, headers=headers, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()

        if len(response.content) > _METADATA_MAX_BYTES:
            raise ArtifactDownloadError(
                f"npm registry metadata response for {self.package}@{self.version} exceeds size limit "
                f"({len(response.content)} bytes)"
            )

        tarball_url = response.json().get("dist", {}).get("tarball")
        if not tarball_url:
            raise ArtifactDownloadError(
                f"npm registry response for {self.package}@{self.version} did not include dist.tarball"
            )
        return tarball_url
