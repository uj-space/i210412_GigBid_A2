"""Integration tests for Part D: FastAPI endpoints, SSE streaming, approvals, and degraded mode."""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_health_and_openapi_schema():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "marketplace_degraded" in body

    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    paths = spec.json()["paths"]
    for required in (
        "/api/auth/login",
        "/api/jobs/search",
        "/api/jobs/analyze",
        "/api/approvals/respond",
        "/api/messages",
        "/api/runs",
        "/api/runs/{thread_id}/stream",
        "/api/analytics",
        "/api/settings",
    ):
        assert required in paths


def test_auth_login_and_job_search():
    login = client.post("/api/auth/login", json={"name": "Test User", "persona": "AI/ML Engineer"})
    assert login.status_code == 200
    token = login.json()["token"]
    assert token

    res = client.get("/api/jobs/search?q=Python&limit=5", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["degraded"] is False
    assert len(data["jobs"]) >= 1


def test_analyze_interrupt_and_approve_flow():
    job = {
        "job_id": "api-test-001",
        "persona": "ai_ml_engineer",
        "title": "Build Multi-Agent LangGraph RAG Pipeline",
        "description": "Need Python, LangGraph, FastAPI, ChromaDB engineer to build production RAG API.",
        "required_skills": ["Python", "LangGraph", "FastAPI", "ChromaDB"],
        "budget": {"min": 800, "max": 2400},
        "connects_cost": 6,
        "client_id": "client-001",
        "warning_signals": [],
    }
    ana = client.post("/api/jobs/analyze", json={"job": job, "user_id": "api-user"})
    assert ana.status_code == 200
    payload = ana.json()
    assert payload["needs_approval"] is True
    tid = payload["thread_id"]

    # SSE stream endpoint returns text/event-stream
    stream = client.get(f"/api/runs/{tid}/stream")
    assert stream.status_code == 200
    assert "text/event-stream" in stream.headers.get("content-type", "")

    # Approve proposal
    app_res = client.post("/api/approvals/respond", json={"thread_id": tid, "action": "approved"})
    assert app_res.status_code == 200
    assert app_res.json()["approval_status"] == "approved"


def test_degraded_mode_toggle_and_banner_signal():
    try:
        r1 = client.post("/api/marketplace/degraded?flag=true")
        assert r1.status_code == 200
        h = client.get("/api/health").json()
        assert h["marketplace_degraded"] is True
        s = client.get("/api/jobs/search?q=Python").json()
        assert s["degraded"] is True
    finally:
        client.post("/api/marketplace/degraded?flag=false")
        assert client.get("/api/health").json()["marketplace_degraded"] is False


def test_analytics_pipeline_messages_and_settings():
    assert client.get("/api/analytics").status_code == 200
    assert client.get("/api/pipeline").status_code == 200
    msgs = client.get("/api/messages")
    assert msgs.status_code == 200
    msg_list = msgs.json()["messages"]
    assert len(msg_list) >= 1

    # Full Messages Inbox -> Draft AI Reply -> Approve & Send flow
    resp = client.post(
        "/api/messages/respond",
        json={"client_message": msg_list[0], "user_id": "msg-test-user"},
    )
    assert resp.status_code == 200
    tid = resp.json()["thread_id"]
    assert resp.json()["needs_approval"] is True

    app_msg = client.post(
        "/api/messages/approve",
        json={"thread_id": tid, "action": "edited", "edit": {"body": "Sounds great, let us meet tomorrow at 10am UTC."}},
    )
    assert app_msg.status_code == 200
    assert app_msg.json()["result"]["approval_status"] == "edited"

    assert client.get("/api/connects").status_code == 200

    # Settings PUT + GET
    put_s = client.put("/api/settings", json={"rag_variant": "v3", "rate_floor": 55})
    assert put_s.status_code == 200
    get_s = client.get("/api/settings")
    assert get_s.status_code == 200
    assert get_s.json()["settings"]["rag_variant"] == "v3"

    # Long-Term Memory GET + DELETE
    from agent.memory.store import get_memory_store

    store = get_memory_store()
    store.record_outcome("mem-test-user", "ai_ml", "won", evidence_count=1)
    m_before = client.get("/api/memory?user_id=mem-test-user").json()
    assert len(m_before["outcome"]) >= 1
    del_m = client.delete("/api/memory?user_id=mem-test-user")
    assert del_m.status_code == 200
    m_after = client.get("/api/memory?user_id=mem-test-user").json()
    assert m_after["style"] == [] and m_after["outcome"] == []
