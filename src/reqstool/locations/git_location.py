# Copyright © LFV

import logging
import re
from typing import Optional

from pydantic import SecretStr, field_validator
from pygit2 import Commit, GitError, RemoteCallbacks, UserPass, clone_repository
from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.exceptions import GitRefNotFoundError
from reqstool.locations.location import LocationInterface, make_safe_tmpdir_suffix

# Accepted ref characters: alphanumerics, '.', '/', '-', '_'.
# Rejects control chars, '..', shell-special chars, and git revision syntax (@{, ~, ^, :).
_VALID_REF_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/\-]*$")


@Requirements("REQ_002")
class GitLocation(LocationInterface):
    url: str
    ref: str
    token: Optional[SecretStr] = None
    path: str = ""

    @field_validator("ref")
    @classmethod
    def _validate_ref(cls, v: str) -> str:
        if not _VALID_REF_RE.match(v) or ".." in v:
            raise ValueError(
                f"Invalid git ref '{v}': must start with an alphanumeric and contain only "
                "alphanumerics, '.', '/', '-', '_'; '..' is not allowed."
            )
        return v

    def tmpdir_key(self) -> str:
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(self.url)
        if parsed.username or parsed.password:
            host = parsed.hostname or ""
            parsed = parsed._replace(netloc=host + (f":{parsed.port}" if parsed.port else ""))
        return make_safe_tmpdir_suffix("git", f"{urlunparse(parsed)}@{self.ref}")

    def _make_available_on_localdisk(self, dst_path: str) -> str:
        api_token = self.token.get_secret_value() if self.token else None
        callbacks = self.MyRemoteCallbacks(api_token) if api_token else None

        repo = clone_repository(url=self.url, path=dst_path, callbacks=callbacks)

        # Try direct lookup first (tag, default branch, or commit SHA), then fall back to the
        # remote-tracking ref — non-default branches only exist as origin/<ref> after a plain clone.
        obj = None
        for name in (self.ref, f"origin/{self.ref}"):
            try:
                obj = repo.revparse_single(name)
                break
            except (KeyError, GitError):
                continue
        if obj is None:
            raise GitRefNotFoundError(self.ref, self.url)

        commit = obj.peel(Commit)
        repo.checkout_tree(commit)
        repo.set_head(commit.id)  # passing an Oid always results in a detached HEAD

        logging.debug(f"Cloned repo {self.url} (ref: {self.ref}) to {repo.workdir}\n")

        return repo.workdir

    class MyRemoteCallbacks(RemoteCallbacks):
        def __init__(self, api_token):
            self.auth_method = ""  # x-oauth-basic, x-access-token
            self.api_token = api_token

        def credentials(self, url, username_from_url, allowed_types):
            return UserPass(username=self.auth_method, password=self.api_token)
