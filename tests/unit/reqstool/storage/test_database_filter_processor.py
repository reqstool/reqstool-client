# Copyright © LFV

import pytest

from reqstool.common.models.urn_id import UrnId
from reqstool.filters.requirements_filters import RequirementFilter
from reqstool.filters.svcs_filters import SVCFilter
from reqstool.models.mvrs import MVRData, MVRsData
from reqstool.models.raw_datasets import RawDataset
from reqstool.models.requirements import (
    SIGNIFICANCETYPES,
    VARIANTS,
    MetaData,
    RequirementData,
    RequirementsData,
)
from reqstool.models.svcs import SVCData, SVCsData, VERIFICATIONTYPES
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.database_filter_processor import DatabaseFilterProcessor
from reqstool.storage.populator import DatabasePopulator


def _make_req(urn, req_id):
    return RequirementData(
        id=UrnId(urn=urn, id=req_id),
        title=f"Req {req_id}",
        significance=SIGNIFICANCETYPES.SHALL,
        description=f"Description for {req_id}",
        revision="1.0.0",
    )


def _make_svc(urn, svc_id, req_ids):
    return SVCData(
        id=UrnId(urn=urn, id=svc_id),
        title=f"SVC {svc_id}",
        verification=VERIFICATIONTYPES.AUTOMATED_TEST,
        revision="1.0.0",
        requirement_ids=[
            UrnId(urn=uid.split(":")[0], id=uid.split(":")[1]) if ":" in uid else UrnId(urn=urn, id=uid)
            for uid in req_ids
        ],
    )


def _make_mvr(urn, mvr_id, svc_ids):
    return MVRData(
        id=UrnId(urn=urn, id=mvr_id),
        passed=True,
        svc_ids=[
            UrnId(urn=uid.split(":")[0], id=uid.split(":")[1]) if ":" in uid else UrnId(urn=urn, id=uid)
            for uid in svc_ids
        ],
    )


def _setup_db_with_raw_datasets(raw_datasets, parsing_graph, initial_urn):
    """Helper: create DB, populate, set metadata, return (db, raw_datasets dict)."""
    db = RequirementsDatabase()

    db.set_metadata("initial_urn", initial_urn)

    for urn, rd in raw_datasets.items():
        db.insert_urn_metadata(rd.requirements_data.metadata)
        DatabasePopulator.populate_from_raw_dataset(db, urn, rd)

    for parent, children in parsing_graph.items():
        for child in children:
            db.insert_parsing_graph_edge(parent, child)

    return db


@pytest.fixture
def simple_system_with_filter():
    """sys-001 imports ms-001. sys-001 has a filter that excludes REQ_B from sys-001."""
    sys_req_a = _make_req("sys-001", "REQ_A")
    sys_req_b = _make_req("sys-001", "REQ_B")
    sys_req_c = _make_req("sys-001", "REQ_C")

    ms_req_x = _make_req("ms-001", "REQ_X")

    sys_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="sys-001", variant=VARIANTS.SYSTEM, title="System"),
            requirements={
                sys_req_a.id: sys_req_a,
                sys_req_b.id: sys_req_b,
                sys_req_c.id: sys_req_c,
            },
        ),
    )

    ms_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="Microservice"),
            requirements={ms_req_x.id: ms_req_x},
            filters={
                "sys-001": RequirementFilter(
                    urn_ids_excludes={UrnId(urn="sys-001", id="REQ_B")},
                ),
            },
        ),
    )

    raw_datasets = {"ms-001": ms_rd, "sys-001": sys_rd}
    parsing_graph = {"ms-001": ["sys-001"], "sys-001": []}

    db = _setup_db_with_raw_datasets(raw_datasets, parsing_graph, "ms-001")
    return db, raw_datasets


def test_filter_excludes_requirement(simple_system_with_filter):
    db, raw_datasets = simple_system_with_filter

    processor = DatabaseFilterProcessor(db, raw_datasets)
    processor.apply_filters()

    remaining = {row["id"] for row in db.connection.execute("SELECT id FROM requirements").fetchall()}
    assert "REQ_A" in remaining
    assert "REQ_B" not in remaining
    assert "REQ_C" in remaining
    assert "REQ_X" in remaining

    db.close()


def test_filter_includes_requirement():
    """ms-001 imports sys-001, filter includes only REQ_A from sys-001."""
    sys_req_a = _make_req("sys-001", "REQ_A")
    sys_req_b = _make_req("sys-001", "REQ_B")

    ms_req_x = _make_req("ms-001", "REQ_X")

    sys_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="sys-001", variant=VARIANTS.SYSTEM, title="System"),
            requirements={sys_req_a.id: sys_req_a, sys_req_b.id: sys_req_b},
        ),
    )

    ms_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="Microservice"),
            requirements={ms_req_x.id: ms_req_x},
            filters={
                "sys-001": RequirementFilter(
                    urn_ids_imports={UrnId(urn="sys-001", id="REQ_A")},
                ),
            },
        ),
    )

    raw_datasets = {"ms-001": ms_rd, "sys-001": sys_rd}
    parsing_graph = {"ms-001": ["sys-001"], "sys-001": []}

    db = _setup_db_with_raw_datasets(raw_datasets, parsing_graph, "ms-001")
    processor = DatabaseFilterProcessor(db, raw_datasets)
    processor.apply_filters()

    remaining = {row["id"] for row in db.connection.execute("SELECT id FROM requirements").fetchall()}
    assert remaining == {"REQ_A", "REQ_X"}

    db.close()


def test_filter_with_custom_el_exclude():
    """Custom EL exclude expression: exclude REQ_B via expression language."""
    sys_req_a = _make_req("sys-001", "REQ_A")
    sys_req_b = _make_req("sys-001", "REQ_B")

    ms_req_x = _make_req("ms-001", "REQ_X")

    sys_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="sys-001", variant=VARIANTS.SYSTEM, title="System"),
            requirements={sys_req_a.id: sys_req_a, sys_req_b.id: sys_req_b},
        ),
    )

    ms_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="Microservice"),
            requirements={ms_req_x.id: ms_req_x},
            filters={
                "sys-001": RequirementFilter(
                    custom_exclude='ids == "REQ_B"',
                ),
            },
        ),
    )

    raw_datasets = {"ms-001": ms_rd, "sys-001": sys_rd}
    parsing_graph = {"ms-001": ["sys-001"], "sys-001": []}

    db = _setup_db_with_raw_datasets(raw_datasets, parsing_graph, "ms-001")
    processor = DatabaseFilterProcessor(db, raw_datasets)
    processor.apply_filters()

    remaining = {row["id"] for row in db.connection.execute("SELECT id FROM requirements").fetchall()}
    assert remaining == {"REQ_A", "REQ_X"}

    db.close()


def test_filter_with_custom_el_regex_import():
    """Custom EL import with regex: only import requirements matching /REQ_A.*/."""
    sys_req_a1 = _make_req("sys-001", "REQ_A1")
    sys_req_a2 = _make_req("sys-001", "REQ_A2")
    sys_req_b1 = _make_req("sys-001", "REQ_B1")

    ms_req_x = _make_req("ms-001", "REQ_X")

    sys_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="sys-001", variant=VARIANTS.SYSTEM, title="System"),
            requirements={
                sys_req_a1.id: sys_req_a1,
                sys_req_a2.id: sys_req_a2,
                sys_req_b1.id: sys_req_b1,
            },
        ),
    )

    ms_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="Microservice"),
            requirements={ms_req_x.id: ms_req_x},
            filters={
                "sys-001": RequirementFilter(
                    custom_imports="ids == /REQ_A.*/",
                ),
            },
        ),
    )

    raw_datasets = {"ms-001": ms_rd, "sys-001": sys_rd}
    parsing_graph = {"ms-001": ["sys-001"], "sys-001": []}

    db = _setup_db_with_raw_datasets(raw_datasets, parsing_graph, "ms-001")
    processor = DatabaseFilterProcessor(db, raw_datasets)
    processor.apply_filters()

    remaining = {row["id"] for row in db.connection.execute("SELECT id FROM requirements").fetchall()}
    assert remaining == {"REQ_A1", "REQ_A2", "REQ_X"}

    db.close()


def test_filter_cascades_to_svc_and_mvr():
    """Deleting a requirement cascades: SVC with no remaining reqs is deleted, MVR with no remaining SVCs is deleted."""
    sys_req_a = _make_req("sys-001", "REQ_A")
    sys_req_b = _make_req("sys-001", "REQ_B")
    sys_svc = _make_svc("sys-001", "SVC_1", ["REQ_B"])
    sys_mvr = _make_mvr("sys-001", "MVR_1", ["SVC_1"])

    ms_req_x = _make_req("ms-001", "REQ_X")

    sys_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="sys-001", variant=VARIANTS.SYSTEM, title="System"),
            requirements={sys_req_a.id: sys_req_a, sys_req_b.id: sys_req_b},
        ),
        svcs_data=SVCsData(cases={sys_svc.id: sys_svc}),
        mvrs_data=MVRsData(results={sys_mvr.id: sys_mvr}),
    )

    ms_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="Microservice"),
            requirements={ms_req_x.id: ms_req_x},
            filters={
                "sys-001": RequirementFilter(
                    urn_ids_excludes={UrnId(urn="sys-001", id="REQ_B")},
                ),
            },
        ),
    )

    raw_datasets = {"ms-001": ms_rd, "sys-001": sys_rd}
    parsing_graph = {"ms-001": ["sys-001"], "sys-001": []}

    db = _setup_db_with_raw_datasets(raw_datasets, parsing_graph, "ms-001")
    processor = DatabaseFilterProcessor(db, raw_datasets)
    processor.apply_filters()

    assert db.connection.execute("SELECT COUNT(*) FROM requirements").fetchone()[0] == 2  # REQ_A, REQ_X
    assert db.connection.execute("SELECT COUNT(*) FROM svcs").fetchone()[0] == 0  # SVC_1 deleted (linked only to REQ_B)
    assert db.connection.execute("SELECT COUNT(*) FROM mvrs").fetchone()[0] == 0  # MVR_1 deleted (linked only to SVC_1)

    db.close()


def test_no_filters_keeps_everything():
    """No filters defined: all data should remain."""
    sys_req = _make_req("sys-001", "REQ_A")
    ms_req = _make_req("ms-001", "REQ_X")

    sys_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="sys-001", variant=VARIANTS.SYSTEM, title="System"),
            requirements={sys_req.id: sys_req},
        ),
    )

    ms_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="Microservice"),
            requirements={ms_req.id: ms_req},
        ),
    )

    raw_datasets = {"ms-001": ms_rd, "sys-001": sys_rd}
    parsing_graph = {"ms-001": ["sys-001"], "sys-001": []}

    db = _setup_db_with_raw_datasets(raw_datasets, parsing_graph, "ms-001")
    processor = DatabaseFilterProcessor(db, raw_datasets)
    processor.apply_filters()

    assert db.connection.execute("SELECT COUNT(*) FROM requirements").fetchone()[0] == 2
    assert db.get_metadata("filtered") == "true"

    db.close()


def test_svc_filter_excludes():
    """SVC filter excludes SVC_B."""
    sys_req = _make_req("sys-001", "REQ_A")
    sys_svc_a = _make_svc("sys-001", "SVC_A", ["REQ_A"])
    sys_svc_b = _make_svc("sys-001", "SVC_B", ["REQ_A"])

    ms_req = _make_req("ms-001", "REQ_X")

    sys_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="sys-001", variant=VARIANTS.SYSTEM, title="System"),
            requirements={sys_req.id: sys_req},
        ),
        svcs_data=SVCsData(cases={sys_svc_a.id: sys_svc_a, sys_svc_b.id: sys_svc_b}),
    )

    ms_rd = RawDataset(
        requirements_data=RequirementsData(
            metadata=MetaData(urn="ms-001", variant=VARIANTS.MICROSERVICE, title="Microservice"),
            requirements={ms_req.id: ms_req},
        ),
        svcs_data=SVCsData(
            filters={
                "sys-001": SVCFilter(
                    urn_ids_excludes={UrnId(urn="sys-001", id="SVC_B")},
                ),
            },
        ),
    )

    raw_datasets = {"ms-001": ms_rd, "sys-001": sys_rd}
    parsing_graph = {"ms-001": ["sys-001"], "sys-001": []}

    db = _setup_db_with_raw_datasets(raw_datasets, parsing_graph, "ms-001")
    processor = DatabaseFilterProcessor(db, raw_datasets)
    processor.apply_filters()

    remaining_svcs = {row["id"] for row in db.connection.execute("SELECT id FROM svcs").fetchall()}
    assert remaining_svcs == {"SVC_A"}

    db.close()
