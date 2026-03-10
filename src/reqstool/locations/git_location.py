# Copyright © LFV

import logging
import os
from typing import Optional

from pygit2 import RemoteCallbacks, UserPass, clone_repository
from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.locations.location import LocationInterface


@Requirements("REQ_002")
class GitLocation(LocationInterface):
    url: str
    branch: str
    env_token: Optional[str] = None
    path: str

    def _make_available_on_localdisk(self, dst_path: str) -> str:
        api_token = os.getenv(self.env_token)

        if self.branch:
            repo = clone_repository(
                url=self.url, path=dst_path, checkout_branch=self.branch, callbacks=self.MyRemoteCallbacks(api_token)
            )
        else:
            repo = clone_repository(url=self.url, path=dst_path, callbacks=self.MyRemoteCallbacks(api_token))

        logging.debug(f"Cloned repo {self.url} (branch: {self.branch}) to {repo.workdir}\n")

        return repo.workdir

    class MyRemoteCallbacks(RemoteCallbacks):
        def __init__(self, api_token):
            self.auth_method = ""  # x-oauth-basic, x-access-token
            self.api_token = api_token

        def credentials(self, url, username_from_url, allowed_types):
            return UserPass(username=self.auth_method, password=self.api_token)
