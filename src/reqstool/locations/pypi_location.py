import logging
import os
import re
import sys
import tarfile
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from reqstool.common.utils import Utils
from reqstool.locations.location import LocationInterface


@dataclass(kw_only=True)
class PypiLocation(LocationInterface):
    url: str = field(default="https://pypi.org/simple")
    package: str
    version: str
    env_token: Optional[str] = field(default=None)

    @staticmethod
    def normalize_pypi_package_name(package_name):
        return re.sub(r"[-_.]+", "-", package_name).lower()

    def _make_available_on_localdisk(self, dst_path: str):
        """
        Download the PyPI package and extract it to the local disk.
        """
        # Retrieve token from environment variable
        token = os.getenv(self.env_token)

        if token:
            logging.debug("Using OAuth Bearer token for authentication")

        package_url = self.get_package_url(self.package, self.version, self.url, token)

        if not package_url:
            token_info = f"(with token in environment variable '{self.env_token}')" if self.env_token else ""
            raise RuntimeError(
                f"Unable to find a sdist pypi package for {self.package} == {self.version} in repo {self.url}{token_info}"
            )

        logging.debug(f"Downloading {self.package} from {self.url} to {dst_path}\n")

        try:
            downloaded_file = Utils.download_file(url=package_url, dst_path=dst_path, token=token)

            logging.debug(f"Extracting {downloaded_file} to {dst_path}\n")

            with tarfile.open(downloaded_file, "r:gz") as tar_ref:
                top_level_dirs = {
                    member.name.split("/")[0] for member in tar_ref.getmembers() if member.name.count("/") > 0
                }
                tar_ref.extractall(path=dst_path, filter="data")
        except tarfile.TarError as e:
            logging.fatal(f"Error extracting {downloaded_file}: {e}")
            sys.exit(1)
        except Exception as e:
            logging.fatal(
                f"Error when downloading etc sdist pypi package for {self.package}=={self.version}"
                f" in repo {self.url} {'with token' if token else ''}",
                e,
            )
            sys.exit(1)

        if len(top_level_dirs) != 1:
            logging.fatal(
                f"Tarball from {self.url} did not have one and only one" f" top level directory: {top_level_dirs}"
            )
            sys.exit(1)

        top_level_dir = os.path.join(dst_path, top_level_dirs.pop())

        logging.debug(f"Extracted {downloaded_file} to {top_level_dir}\n")

        return top_level_dir

    @staticmethod
    def get_package_url(package, version, base_url, token) -> str:
        package = PypiLocation.normalize_pypi_package_name(package_name=package)

        if not base_url.endswith("/"):
            base_url += "/"

        # Construct the request URL by appending the package_name to base_url_path
        url = urljoin(base_url, f"{package}/")

        # Prepare headers
        headers = {"Accept": "text/html"}

        if token:
            # If the token exists, add it as a Bearer token in the Authorization header
            headers["Authorization"] = f"Bearer {token}"

        # Make the request to the package's metadata endpoint
        response = requests.get(url, headers=headers)

        # Raise an error if the request was unsuccessful
        response.raise_for_status()

        # Parse the HTML response
        soup = BeautifulSoup(response.content, "html.parser")

        # Search for the specific version's sdist file
        for link in soup.find_all("a"):
            href = link.get("href")
            if href and f"{version}.tar.gz" in href:
                # Normalize the URL by removing the has suffix if present (e.g. md5, sha1, sha224, sha256, sha384, sha512)
                if "#" in href:
                    href = href.split("#")[0]  # Remove the hash suffix

                absolute_url = urljoin(url, href)
                return absolute_url  # Return the absolute URL of the matching file

        # Return None if no matching file is found
        return None
