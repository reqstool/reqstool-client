# Copyright © LFV


import logging

from reqstool.common.models.urn_id import UrnId
from reqstool.filters.id_filters import IDFilters
from reqstool.models.raw_datasets import RawDataset
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.el_to_sql_compiler import ELToSQLCompiler

logger = logging.getLogger(__name__)


class DatabaseFilterProcessor:
    def __init__(self, db: RequirementsDatabase, raw_datasets: dict[str, RawDataset]):
        self._db = db
        self._raw_datasets = raw_datasets
        self._parsing_graph = self._load_parsing_graph()

    def apply_filters(self) -> None:
        self._remove_implementation_requirements()

        initial_urn = self._db.get_metadata("initial_urn")

        self._apply_req_filters(initial_urn)
        self._apply_svc_filters(initial_urn)

        self._db.set_metadata("filtered", "true")

    def _remove_implementation_requirements(self) -> None:
        """Delete requirements from nodes only reachable via implementation edges.

        Nodes reachable only via implementation edges are evidence contributors, not
        requirement definers. Their requirements are out of scope from the initial URN's
        perspective. CASCADE removes SVCs/MVRs/annotations that only linked to those
        requirements; evidence rows linking to in-scope requirements survive.
        """
        self._db.connection.execute(
            """
            DELETE FROM requirements WHERE urn IN (
                SELECT DISTINCT child_urn FROM parsing_graph WHERE edge_type = 'implementation'
                EXCEPT
                SELECT DISTINCT child_urn FROM parsing_graph WHERE edge_type = 'import'
                EXCEPT
                SELECT value FROM metadata WHERE key = 'initial_urn'
            )
            """
        )
        self._db.connection.commit()

    # -- Requirement filters --

    def _apply_req_filters(self, initial_urn: str) -> None:
        logger.debug(f"Starting filtering of requirements from {initial_urn}")

        kept_requirements, _ = self._process_req_filters_per_urn(initial_urn)

        all_reqs = {
            UrnId(urn=row["urn"], id=row["id"])
            for row in self._db.connection.execute("SELECT urn, id FROM requirements").fetchall()
        }

        to_delete = all_reqs - kept_requirements
        logger.debug(f"Deleting {len(to_delete)} requirements")

        for req_uid in to_delete:
            self._delete_requirement(req_uid)

    def _process_req_filters_per_urn(self, urn: str) -> tuple[set[UrnId], set[UrnId]]:
        kept_imports: set[UrnId] = set()
        filtered_out_imports: set[UrnId] = set()

        for import_urn, edge_type in self._parsing_graph.get(urn, []):
            if edge_type == "implementation":
                continue

            kept_per_import, filtered_per_import = self._process_req_filters_per_urn(import_urn)
            kept_imports.update(kept_per_import)
            filtered_out_imports.update(filtered_per_import)

        filtered_out: set[UrnId] = set()

        reqdata = self._raw_datasets[urn].requirements_data
        for filter_urn, req_filter in reqdata.filters.items():
            accessible_per_filter = {r for r in kept_imports if r.urn == filter_urn}

            self._check_filter_refs(req_filter, accessible_per_filter)

            filtered_per_filter = self._get_filtered_out(
                accessible=accessible_per_filter,
                urn=filter_urn,
                id_filter=req_filter,
                table="requirements",
            )
            filtered_out.update(filtered_per_filter)

        kept = kept_imports - filtered_out
        own_reqs = {
            UrnId(urn=row["urn"], id=row["id"])
            for row in self._db.connection.execute("SELECT urn, id FROM requirements WHERE urn = ?", (urn,)).fetchall()
        }
        kept.update(own_reqs)

        filtered_out.update(filtered_out_imports)

        return kept, filtered_out

    # -- SVC filters --

    def _apply_svc_filters(self, initial_urn: str) -> None:
        logger.debug(f"Starting filtering of svcs from {initial_urn}")

        _, filtered_out_svcs = self._process_svc_filters_per_urn(initial_urn)

        logger.debug(f"Deleting {len(filtered_out_svcs)} svcs")

        for svc_uid in filtered_out_svcs:
            self._delete_svc(svc_uid)

    def _process_svc_filters_per_urn(self, urn: str) -> tuple[set[UrnId], set[UrnId]]:
        kept_imports: set[UrnId] = set()
        filtered_out_imports: set[UrnId] = set()

        for import_urn, edge_type in self._parsing_graph.get(urn, []):
            if edge_type == "implementation":
                continue

            kept_per_import, filtered_per_import = self._process_svc_filters_per_urn(import_urn)
            kept_imports.update(kept_per_import)
            filtered_out_imports.update(filtered_per_import)

        filtered_out: set[UrnId] = set()

        svcdata = self._raw_datasets[urn].svcs_data
        if svcdata:
            for filter_urn, svc_filter in svcdata.filters.items():
                accessible_per_filter = {s for s in kept_imports if s.urn == filter_urn}

                self._check_filter_refs(svc_filter, accessible_per_filter)

                filtered_per_filter = self._get_filtered_out(
                    accessible=accessible_per_filter,
                    urn=filter_urn,
                    id_filter=svc_filter,
                    table="svcs",
                )
                filtered_out.update(filtered_per_filter)

        kept = kept_imports - filtered_out
        own_svcs = {
            UrnId(urn=row["urn"], id=row["id"])
            for row in self._db.connection.execute("SELECT urn, id FROM svcs WHERE urn = ?", (urn,)).fetchall()
        }
        kept.update(own_svcs)

        filtered_out.update(filtered_out_imports)

        return kept, filtered_out

    # -- Shared helpers --

    def _get_filtered_out(self, accessible: set[UrnId], urn: str, id_filter: IDFilters, table: str) -> set[UrnId]:
        tree_custom_imports = None
        tree_custom_exclude = None

        if id_filter.custom_imports is not None:
            tree_custom_imports = ELToSQLCompiler.compile(id_filter.custom_imports, urn)
        if id_filter.custom_exclude is not None:
            tree_custom_exclude = ELToSQLCompiler.compile(id_filter.custom_exclude, urn)

        filtered_out: set[UrnId] = set()

        for uid in accessible:
            imports_item = True

            if id_filter.urn_ids_excludes or tree_custom_exclude:
                b_ids_excludes = uid in id_filter.urn_ids_excludes if id_filter.urn_ids_excludes else False

                b_custom_exclude = False
                if tree_custom_exclude:
                    b_custom_exclude = self._eval_compiled_el(tree_custom_exclude, uid, table)

                imports_item = not (b_ids_excludes or b_custom_exclude)

            elif id_filter.urn_ids_imports or tree_custom_imports:
                b_ids_imports = uid in id_filter.urn_ids_imports if id_filter.urn_ids_imports else False

                b_custom_imports = False
                if tree_custom_imports:
                    b_custom_imports = self._eval_compiled_el(tree_custom_imports, uid, table)

                imports_item = b_ids_imports or b_custom_imports

            if not imports_item:
                filtered_out.add(uid)

        return filtered_out

    _ALLOWED_FILTER_TABLES = frozenset({"requirements", "svcs"})

    def _eval_compiled_el(self, compiled: tuple[str, list], uid: UrnId, table: str) -> bool:
        if table not in self._ALLOWED_FILTER_TABLES:
            raise ValueError(f"Invalid table for filter evaluation: {table}")
        where_clause, params = compiled
        row = self._db.connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE urn = ? AND id = ? AND {where_clause}",  # noqa: S608
            [uid.urn, uid.id] + params,
        ).fetchone()
        return row[0] > 0

    def _delete_requirement(self, req_uid: UrnId) -> None:
        logger.debug(f"Deleting requirement: {req_uid}")

        # Find SVCs linked only to this requirement — they should be deleted too
        linked_svcs = self._db.connection.execute(
            "SELECT svc_urn, svc_id FROM svc_requirement_links WHERE req_urn = ? AND req_id = ?",
            (req_uid.urn, req_uid.id),
        ).fetchall()

        self._db.connection.execute("DELETE FROM requirements WHERE urn = ? AND id = ?", (req_uid.urn, req_uid.id))

        # Delete SVCs that no longer link to any requirements (CASCADE removed the link rows)
        for row in linked_svcs:
            remaining = self._db.connection.execute(
                "SELECT COUNT(*) FROM svc_requirement_links WHERE svc_urn = ? AND svc_id = ?",
                (row["svc_urn"], row["svc_id"]),
            ).fetchone()[0]
            if remaining == 0:
                self._delete_svc(UrnId(urn=row["svc_urn"], id=row["svc_id"]))

        self._db.connection.commit()

    def _delete_svc(self, svc_uid: UrnId) -> None:
        logger.debug(f"Deleting svc: {svc_uid}")

        linked_mvrs = self._db.connection.execute(
            "SELECT mvr_urn, mvr_id FROM mvr_svc_links WHERE svc_urn = ? AND svc_id = ?",
            (svc_uid.urn, svc_uid.id),
        ).fetchall()

        self._db.connection.execute("DELETE FROM svcs WHERE urn = ? AND id = ?", (svc_uid.urn, svc_uid.id))

        # Delete MVRs that no longer link to any SVCs
        for row in linked_mvrs:
            remaining = self._db.connection.execute(
                "SELECT COUNT(*) FROM mvr_svc_links WHERE mvr_urn = ? AND mvr_id = ?",
                (row["mvr_urn"], row["mvr_id"]),
            ).fetchone()[0]
            if remaining == 0:
                self._db.connection.execute(
                    "DELETE FROM mvrs WHERE urn = ? AND id = ?", (row["mvr_urn"], row["mvr_id"])
                )

        self._db.connection.commit()

    def _check_filter_refs(self, id_filter: IDFilters, accessible: set[UrnId]) -> None:
        if id_filter.urn_ids_imports:
            for uid in id_filter.urn_ids_imports:
                if uid not in accessible:
                    logger.warning(f"Cannot import: {uid} does not exist or is not accessible")
        elif id_filter.urn_ids_excludes:
            for uid in id_filter.urn_ids_excludes:
                if uid not in accessible:
                    logger.warning(f"Cannot exclude: {uid} does not exist or is not accessible")

    def _load_parsing_graph(self) -> dict[str, list[tuple[str, str]]]:
        graph: dict[str, list[tuple[str, str]]] = {}
        rows = self._db.connection.execute("SELECT parent_urn, child_urn, edge_type FROM parsing_graph").fetchall()
        # Initialize all URNs as keys (including leaves with no children)
        all_urns = {row["urn"] for row in self._db.connection.execute("SELECT urn FROM urn_metadata").fetchall()}
        for urn in all_urns:
            graph[urn] = []
        for row in rows:
            graph.setdefault(row["parent_urn"], []).append((row["child_urn"], row["edge_type"]))
        return graph
