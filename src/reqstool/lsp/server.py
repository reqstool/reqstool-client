# Copyright © LFV

from __future__ import annotations

import logging

from lsprotocol import types
from pygls.lsp.server import LanguageServer

from reqstool.lsp.features.completion import handle_completion
from reqstool.lsp.features.definition import handle_definition
from reqstool.lsp.features.diagnostics import compute_diagnostics
from reqstool.lsp.features.hover import handle_hover
from reqstool.lsp.workspace_manager import WorkspaceManager

logger = logging.getLogger(__name__)

SERVER_NAME = "reqstool"
SERVER_VERSION = "0.1.0"


class ReqstoolLanguageServer(LanguageServer):
    def __init__(self):
        super().__init__(name=SERVER_NAME, version=SERVER_VERSION)
        self.workspace_manager = WorkspaceManager()


server = ReqstoolLanguageServer()


# -- Lifecycle handlers --


@server.feature(types.INITIALIZED)
def on_initialized(ls: ReqstoolLanguageServer, params: types.InitializedParams) -> None:
    logger.info("reqstool LSP server initialized")
    _discover_and_build(ls)


@server.feature(types.SHUTDOWN)
def on_shutdown(ls: ReqstoolLanguageServer, params: None) -> None:
    logger.info("reqstool LSP server shutting down")
    ls.workspace_manager.close_all()


# -- Document lifecycle --


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def on_did_open(ls: ReqstoolLanguageServer, params: types.DidOpenTextDocumentParams) -> None:
    _publish_diagnostics_for_document(ls, params.text_document.uri)


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def on_did_change(ls: ReqstoolLanguageServer, params: types.DidChangeTextDocumentParams) -> None:
    _publish_diagnostics_for_document(ls, params.text_document.uri)


@server.feature(types.TEXT_DOCUMENT_DID_SAVE)
def on_did_save(ls: ReqstoolLanguageServer, params: types.DidSaveTextDocumentParams) -> None:
    uri = params.text_document.uri
    if WorkspaceManager.is_static_yaml(uri):
        logger.info("Static YAML file saved, rebuilding affected project: %s", uri)
        ls.workspace_manager.rebuild_affected(uri)
        _publish_all_diagnostics(ls)
    else:
        _publish_diagnostics_for_document(ls, uri)


@server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
def on_did_close(ls: ReqstoolLanguageServer, params: types.DidCloseTextDocumentParams) -> None:
    # Clear diagnostics for closed document
    ls.text_document_publish_diagnostics(types.PublishDiagnosticsParams(uri=params.text_document.uri, diagnostics=[]))


# -- Workspace folder changes --


@server.feature(types.WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS)
def on_workspace_folders_changed(ls: ReqstoolLanguageServer, params: types.DidChangeWorkspaceFoldersParams) -> None:
    for removed in params.event.removed:
        logger.info("Workspace folder removed: %s", removed.uri)
        ls.workspace_manager.remove_folder(removed.uri)

    for added in params.event.added:
        logger.info("Workspace folder added: %s", added.uri)
        ls.workspace_manager.add_folder(added.uri)

    _publish_all_diagnostics(ls)


# -- File watcher --


@server.feature(types.WORKSPACE_DID_CHANGE_WATCHED_FILES)
def on_watched_files_changed(ls: ReqstoolLanguageServer, params: types.DidChangeWatchedFilesParams) -> None:
    rebuild_needed = False
    for change in params.changes:
        if WorkspaceManager.is_static_yaml(change.uri):
            logger.info("Watched file changed: %s (type=%s)", change.uri, change.type)
            rebuild_needed = True

    if rebuild_needed:
        ls.workspace_manager.rebuild_all()
        _publish_all_diagnostics(ls)


# -- Commands --


@server.command("reqstool.refresh")
def cmd_refresh(ls: ReqstoolLanguageServer, *args) -> None:
    logger.info("Manual refresh requested")
    ls.workspace_manager.rebuild_all()
    _publish_all_diagnostics(ls)
    ls.window_show_message(types.ShowMessageParams(type=types.MessageType.Info, message="reqstool: projects refreshed"))


# -- Feature handlers --


@server.feature(types.TEXT_DOCUMENT_HOVER)
def on_hover(ls: ReqstoolLanguageServer, params: types.HoverParams) -> types.Hover | None:
    document = ls.workspace.get_text_document(params.text_document.uri)
    project = ls.workspace_manager.project_for_file(params.text_document.uri)
    return handle_hover(
        uri=params.text_document.uri,
        position=params.position,
        text=document.source,
        language_id=document.language_id or "",
        project=project,
    )


@server.feature(
    types.TEXT_DOCUMENT_COMPLETION,
    types.CompletionOptions(trigger_characters=['"', " ", ":"]),
)
def on_completion(ls: ReqstoolLanguageServer, params: types.CompletionParams) -> types.CompletionList | None:
    document = ls.workspace.get_text_document(params.text_document.uri)
    project = ls.workspace_manager.project_for_file(params.text_document.uri)
    return handle_completion(
        uri=params.text_document.uri,
        position=params.position,
        text=document.source,
        language_id=document.language_id or "",
        project=project,
    )


@server.feature(types.TEXT_DOCUMENT_DEFINITION)
def on_definition(ls: ReqstoolLanguageServer, params: types.DefinitionParams) -> list[types.Location]:
    document = ls.workspace.get_text_document(params.text_document.uri)
    project = ls.workspace_manager.project_for_file(params.text_document.uri)
    return handle_definition(
        uri=params.text_document.uri,
        position=params.position,
        text=document.source,
        language_id=document.language_id or "",
        project=project,
    )


# -- Internal helpers --


def _discover_and_build(ls: ReqstoolLanguageServer) -> None:
    """Discover reqstool projects in all workspace folders and build databases."""
    try:
        folders = ls.workspace.folders
    except RuntimeError:
        logger.warning("Workspace not available during initialization")
        return

    if not folders:
        logger.info("No workspace folders found")
        return

    for folder_uri, folder in folders.items():
        logger.info("Discovering reqstool projects in workspace folder: %s", folder.name)
        projects = ls.workspace_manager.add_folder(folder_uri)
        for project in projects:
            if project.ready:
                ls.window_show_message(
                    types.ShowMessageParams(
                        type=types.MessageType.Info,
                        message=f"reqstool: loaded project at {project.reqstool_path}",
                    )
                )
            elif project.error:
                ls.window_show_message(
                    types.ShowMessageParams(
                        type=types.MessageType.Warning,
                        message=f"reqstool: failed to load {project.reqstool_path}: {project.error}",
                    )
                )


def _publish_diagnostics_for_document(ls: ReqstoolLanguageServer, uri: str) -> None:
    """Publish diagnostics for a single document."""
    try:
        document = ls.workspace.get_text_document(uri)
    except Exception:
        return
    project = ls.workspace_manager.project_for_file(uri)
    diagnostics = compute_diagnostics(
        uri=uri,
        text=document.source,
        language_id=document.language_id or "",
        project=project,
    )
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
    )


def _publish_all_diagnostics(ls: ReqstoolLanguageServer) -> None:
    """Re-publish diagnostics for all open documents."""
    for uri in list(ls.workspace.text_documents.keys()):
        _publish_diagnostics_for_document(ls, uri)


def start_server() -> None:
    """Entry point for `reqstool lsp` command."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting reqstool LSP server (stdio)")
    server.start_io()
