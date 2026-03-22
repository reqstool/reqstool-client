# Copyright © LFV

import logging
import os
from typing import Optional

from maven_artifact import Artifact, Downloader, RequestException
from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.exceptions import ArtifactDownloadError, ArtifactExtractionError
from reqstool.common.utils import Utils
from reqstool.locations.location import LocationInterface


@Requirements("REQ_003", "REQ_017")
class MavenLocation(LocationInterface):
    url: Optional[str] = "https://repo.maven.apache.org/maven2"
    group_id: str
    artifact_id: str
    version: str
    classifier: str = "reqstool"
    env_token: Optional[str] = None

    def _make_available_on_localdisk(self, dst_path: str):
        token = os.getenv(self.env_token)

        # assume OAuth Bearer, see: https://georgearisty.dev/posts/oauth2-token-bearer-usage/
        downloader = Downloader(base=self.url, token=token)

        artifact = Artifact(
            group_id=self.group_id,
            artifact_id=self.artifact_id,
            version=self.version,
            classifier=self.classifier,
            extension="zip",
        )

        logging.debug(f"Downloading {artifact} from {self.url} to {dst_path}")

        try:
            if not downloader.download(artifact, filename=dst_path):
                raise RequestException(f"Error downloading artifact {artifact} from: {self.url}")
        except RequestException as e:
            raise ArtifactDownloadError(f"Error downloading artifact {artifact} from {self.url}: {e.msg}") from e

        logging.debug(f"Unzipping {artifact.get_filename(dst_path)} to {dst_path}\n")

        try:
            return Utils.extract_zip(artifact.get_filename(dst_path), dst_path)
        except ValueError as e:
            raise ArtifactExtractionError(f"Maven artifact {artifact} from {self.url}: {e}") from e
