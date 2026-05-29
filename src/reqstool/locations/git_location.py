# Copyright © LFV

import logging
import os
from typing import Optional

from pygit2 import Commit, RemoteCallbacks, UserPass, clone_repository
from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.exceptions import GitRefNotFoundError
from reqstool.locations.location import LocationInterface, make_safe_tmpdir_suffix


@Requirements("REQ_002")
class GitLocation(LocationInterface):
    url: str
    ref: str
    env_token: Optional[str] = None
    path: str = ""

    def tmpdir_key(self) -> str:
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(self.url)
        if parsed.username or parsed.password:
            host = parsed.hostname or ""
            parsed = parsed._replace(netloc=host + (f":{parsed.port}" if parsed.port else ""))
        return make_safe_tmpdir_suffix("git", urlunparse(parsed))

    def _make_available_on_localdisk(self, dst_path: str) -> str:
        api_token = os.getenv(self.env_token) if self.env_token else None

        repo = clone_repository(url=self.url, path=dst_path, callbacks=self.MyRemoteCallbacks(api_token))

        # Resolve ref uniformly: a tag, the default branch, or a commit SHA resolve directly;
        # a non-default branch only exists as a remote-tracking ref (origin/<ref>) after a plain clone.
        try:
            try:
                obj = repo.revparse_single(self.ref)
            except KeyError:
                obj = repo.revparse_single(f"origin/{self.ref}")
        except KeyError as e:
            raise GitRefNotFoundError(self.ref, self.url) from e

        commit = obj.peel(Commit)
        repo.checkout_tree(commit)
        repo.set_head(commit.id)  # Oid detaches HEAD at the resolved commit

        logging.debug(f"Cloned repo {self.url} (ref: {self.ref}) to {repo.workdir}\n")

        return repo.workdir

    class MyRemoteCallbacks(RemoteCallbacks):
        def __init__(self, api_token):
            self.auth_method = ""  # x-oauth-basic, x-access-token
            self.api_token = api_token

        def credentials(self, url, username_from_url, allowed_types):
            return UserPass(username=self.auth_method, password=self.api_token)
