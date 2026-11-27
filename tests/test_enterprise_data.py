"""Tests for the VERITAS AI enterprise data layer (SQLite in-memory)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import enterprise.repositories as repo
from enterprise.config import create_database_engine, get_database_url, init_db
from enterprise.hashing import GENESIS_HASH, audit_hash, canonical_json, sha256
from enterprise.models import Base


MINIMUM_TABLES = {
    "tenants",
    "users",
    "user_tenants",
    "sessions",
    "policies",
    "executions",
    "events",
    "approvals",
    "receipts",
    "anchors",
    "audit_events",
    "tool_registry",
    "egress_deliveries",
}

# tenants/users are identity tables; user_tenants/sessions are tenancy links.
BUSINESS_TABLES = {
    "policies",
    "executions",
    "events",
    "approvals",
    "receipts",
    "anchors",
    "audit_events",
    "tool_registry",
    "egress_deliveries",
    "tool_calls",
    "vendors",
    "agent_configs",
}


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine):
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    session = factory()
    repo.create_tenant(session, id="t-a", name="Tenant A", slug="a")
    repo.create_tenant(session, id="t-b", name="Tenant B", slug="b")
    session.commit()
    yield session
    session.close()


def _execution(session, tenant_id, key, **kwargs):
    return repo.create_execution(
        session,
        tenant_id=tenant_id,
        id=f"exec_{tenant_id}_{key}",
        idempotency_key=key,
        payload_json=canonical_json({"amount_idr": 1}),
        payload_hash=sha256("payload"),
        **kwargs,
    )


# --------------------------------------------------------------------------- helpers / schema


def test_canonical_json_sha256_and_audit_hash():
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert sha256("abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    payload = {"action": "POLICY_UPDATE", "version": 2}
    digest = audit_hash(GENESIS_HASH, payload)
    assert digest == audit_hash(GENESIS_HASH, canonical_json(payload))
    assert len(digest) == 64


def test_url_default_and_psycopg_normalisation(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert get_database_url() == "sqlite:///./enterprise.db"
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/vt")
    assert get_database_url() == "postgresql+psycopg://u:p@db:5432/vt"
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@db/vt")
    assert get_database_url().startswith("postgresql+psycopg://")
    monkeypatch.delenv("DATABASE_URL")


def test_minimum_tables_and_tenant_columns(engine):
    names = set(inspect(engine).get_table_names())
    assert MINIMUM_TABLES <= names
    for table in BUSINESS_TABLES:
        assert "tenant_id" in Base.metadata.tables[table].columns, table
    # identity/tenancy tables are exempt but tenants/user_tenants/sessions still
    # carry a tenant scope in this implementation.
    assert "tenant_id" in Base.metadata.tables["user_tenants"].columns
    assert "tenant_id" in Base.metadata.tables["sessions"].columns


# --------------------------------------------------------------------------- tenant filtering


def test_tenant_filter_is_mandatory(session):
    with pytest.raises(repo.TenantRequired):
        repo.list_executions(session, tenant_id="")
    with pytest.raises(repo.TenantRequired):
        repo.get_execution(session, tenant_id=None, execution_id="exec_x")
    with pytest.raises(TypeError):
        repo.get_execution(session, execution_id="exec_x")  # no tenant_id at all
    with pytest.raises(repo.TenantRequired):
        repo.list_audit_events(session, tenant_id=None)


def test_execution_isolation_and_fields(session):
    ex = _execution(
        session,
        "t-a",
        "k1",
        status="POLICY_CHECK",
        decision="ALLOW",
        reason_code="WITHIN_LIMIT",
        proposal_json=canonical_json({"tool": "approve_invoice"}),
        args_hash=sha256("args"),
        tool="approve_invoice",
        actor="operator-a",
    )
    session.commit()
    assert ex.tool_calls == 0
    assert ex.created_at and ex.updated_at

    assert repo.get_execution(session, tenant_id="t-a", execution_id=ex.id) is not None
    assert repo.get_execution(session, tenant_id="t-b", execution_id=ex.id) is None
    assert repo.list_executions(session, tenant_id="t-b") == []
    assert len(repo.list_executions(session, tenant_id="t-a", status="POLICY_CHECK")) == 1


def test_idempotency_key_unique_per_tenant(session):
    first = _execution(session, "t-a", "same-key")
    second = _execution(session, "t-b", "same-key")
    session.commit()
    assert first.id != second.id
    assert repo.get_execution_by_idempotency_key(session, tenant_id="t-b", idempotency_key="same-key").id == second.id
    with pytest.raises(IntegrityError):
        repo.create_execution(
            session,
            tenant_id="t-a",
            id="exec_t-a_duplicate-key",  # distinct PK, reused idempotency key
            idempotency_key="same-key",
            payload_json=canonical_json({"amount_idr": 1}),
        )
    session.rollback()


# --------------------------------------------------------------------------- approval / evidence


def test_approval_expected_version_and_separation(session):
    ex = _execution(session, "t-a", "k2", status="WAITING_APPROVAL")
    ap = repo.create_approval(
        session,
        tenant_id="t-a",
        id="aprv_1",
        execution_id=ex.id,
        requester="requester-a",
        args_hash=sha256("args"),
        policy_version=1,
    )
    assert ap.version == 1

    decided = repo.decide_approval(
        session,
        tenant_id="t-a",
        approval_id=ap.id,
        expected_version=1,
        decision="approve",
        approver="approver-b",
        reason="reviewed",
    )
    assert decided.status == "approved" and decided.version == 2
    with pytest.raises(repo.VersionConflict):
        repo.decide_approval(
            session,
            tenant_id="t-a",
            approval_id=ap.id,
            expected_version=1,
            decision="approve",
            approver="approver-b",
        )
    assert repo.get_approval(session, tenant_id="t-a", approval_id=ap.id).version == 2
    assert repo.get_approval(session, tenant_id="t-b", approval_id=ap.id) is None

    ex2 = _execution(session, "t-a", "k3", status="WAITING_APPROVAL")
    repo.create_approval(session, tenant_id="t-a", id="aprv_2", execution_id=ex2.id, requester="same-user")
    with pytest.raises(repo.SeparationOfDuties):
        repo.decide_approval(
            session,
            tenant_id="t-a",
            approval_id="aprv_2",
            expected_version=1,
            decision="approve",
            approver="same-user",
        )


def test_receipt_anchor_and_tool_calls(session):
    ex = _execution(session, "t-a", "k4", status="SUCCEEDED", tool="approve_invoice")
    body = {"receipt_id": "rcpt_1", "execution_id": ex.id}
    receipt = repo.create_receipt(
        session,
        tenant_id="t-a",
        id="rcpt_1",
        execution_id=ex.id,
        body_json=canonical_json(body),
        digest=sha256(canonical_json(body)),
        signature="deadbeef",
        key_id="key-1",
    )
    assert receipt.body_json and receipt.digest and receipt.signature and receipt.key_id
    assert repo.get_receipt(session, tenant_id="t-b", receipt_id=receipt.id) is None

    anchor = repo.create_anchor(
        session, tenant_id="t-a", id="anc_1", receipt_id=receipt.id, receipt_hash=receipt.digest
    )
    assert anchor.status == "pending"
    confirmed = repo.set_anchor_status(
        session, tenant_id="t-a", anchor_id=anchor.id, status="confirmed", tx_ref="0xabc"
    )
    assert confirmed.status == "confirmed"
    with pytest.raises(repo.InvalidTransition):
        repo.create_anchor(
            session, tenant_id="t-a", id="anc_2", receipt_id=receipt.id, receipt_hash="x", status="submitted"
        )

    call = repo.record_tool_call(
        session,
        tenant_id="t-a",
        id="call_1",
        execution_id=ex.id,
        tool="approve_invoice",
        idempotency_key="call-key-1",
    )
    assert call.idempotency_key == "call-key-1"
    assert repo.get_execution(session, tenant_id="t-a", execution_id=ex.id).tool_calls == 1
    assert len(repo.list_tool_calls(session, tenant_id="t-a", execution_id=ex.id)) == 1
    assert repo.list_tool_calls(session, tenant_id="t-b", execution_id=ex.id) == []


def test_events_hash_chain_per_execution(session):
    ex = _execution(session, "t-a", "k5")
    prev = GENESIS_HASH
    for etype in ("TASK_CREATED", "POLICY_CHECK"):
        data = {"type": etype}
        digest = audit_hash(prev, canonical_json(data))
        repo.create_event(
            session,
            tenant_id="t-a",
            execution_id=ex.id,
            type=etype,
            data=data,
            prev_hash=prev,
            hash=digest,
        )
        prev = digest
    events = repo.list_events(session, tenant_id="t-a", execution_id=ex.id)
    assert [e.type for e in events] == ["TASK_CREATED", "POLICY_CHECK"]
    assert events[1].prev_hash == events[0].hash
    assert repo.list_events(session, tenant_id="t-b", execution_id=ex.id) == []


# --------------------------------------------------------------------------- audit append-only


def test_audit_hash_chain_scoped_reads_and_append_only(session):
    for i in range(3):
        repo.create_audit_event(
            session,
            tenant_id="t-a",
            actor="admin-a",
            action="POLICY_UPDATE",
            target_type="policy",
            target_id=f"p{i}",
            payload={"version": i + 1},
        )
    repo.create_audit_event(
        session,
        tenant_id="t-b",
        actor="admin-b",
        action="APPROVAL_DECISION",
        target_type="approval",
        target_id="aprv_x",
        payload={"decision": "approve"},
    )
    session.commit()  # keep rows committed: the trigger tests roll back afterwards

    report = repo.verify_audit_chain(session)
    assert report == {"ok": True, "count": 4, "errors": []}

    tenant_a_events = repo.list_audit_events(session, tenant_id="t-a")
    assert len(tenant_a_events) == 3
    assert tenant_a_events[0].prev_hash == GENESIS_HASH
    assert tenant_a_events[1].prev_hash == tenant_a_events[0].hash
    assert len(repo.list_audit_events(session, tenant_id="t-b")) == 1
    assert repo.get_audit_event(session, tenant_id="t-b", seq=tenant_a_events[0].seq) is None

    # Repository exposes no mutation surface for audit_events.
    assert not any(
        hasattr(repo, name)
        for name in ("update_audit_event", "delete_audit_event", "set_audit_event")
    )

    # Database-level guard rejects direct UPDATE/DELETE.
    with pytest.raises(IntegrityError):
        session.execute(
            Base.metadata.tables["audit_events"].update().values(action="TAMPERED")
        )
    session.rollback()
    with pytest.raises(IntegrityError):
        session.execute(Base.metadata.tables["audit_events"].delete())
    session.rollback()
    assert repo.verify_audit_chain(session)["ok"] is True


def test_forged_audit_hash_is_detected(session):
    from sqlalchemy import insert

    table = Base.metadata.tables["audit_events"]
    session.execute(
        insert(table).values(
            tenant_id="t-a",
            actor="attacker",
            action="FORGED",
            target_type="policy",
            target_id="p0",
            payload_json=canonical_json({"x": 1}),
            prev_hash=GENESIS_HASH,
            hash="0" * 64,  # deliberately wrong
            created_at="2026-11-25T00:00:00Z",
        )
    )
    session.flush()
    report = repo.verify_audit_chain(session)
    assert report["ok"] is False
    assert report["errors"] == [1]
