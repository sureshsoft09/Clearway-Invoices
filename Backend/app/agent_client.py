"""Calls the deployed Agent Engine pipeline and streams each step into Firestore.

The streaming matters for the demo: the UI timeline fills in agent by agent instead
of sitting empty for twenty seconds and then jumping to a finished answer.
"""
import json
import time
from typing import Any, Dict

from . import config, store

_remote = None
AGENT_LABELS = {
    "matching_investigate": "Gathering PO, GRN and vendor evidence",
    "matching_conclude": "Classifying the variance",
    "policy_search": "Searching the contract corpus",
    "policy_decide": "Issuing the contractual ruling",
}


def remote():
    global _remote
    if _remote is None:
        if not config.AGENT_ENGINE_RESOURCE:
            raise RuntimeError(
                "AGENT_ENGINE_RESOURCE is not set. Run deploy.py in Src/Agents and "
                "put the printed resource name in .env.")
        import vertexai
        from vertexai import agent_engines
        vertexai.init(project=config.PROJECT, location=config.LOCATION)
        _remote = agent_engines.get(config.AGENT_ENGINE_RESOURCE)
    return _remote


def _as_dict(value: Any) -> Any:
    """Agent output_schema results may arrive as a JSON string."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def run(invoice_id: str, timeout_s: float = 90.0) -> Dict[str, Any]:
    """Run the pipeline for one invoice. Returns the four state keys."""
    agent = remote()
    session = agent.create_session(user_id="backend")
    session_id = session["id"]
    started = time.time()
    seen: set[str] = set()

    store.add_timeline(invoice_id, "agent.started", "Agent Engine pipeline invoked")

    for event in agent.stream_query(
        user_id="backend",
        session_id=session_id,
        message=f"Resolve the exception on invoice {invoice_id}.",
    ):
        author = event.get("author", "")
        if author in AGENT_LABELS and author not in seen:
            seen.add(author)
            store.add_agent_step(invoice_id, {
                "agent": author,
                "label": AGENT_LABELS[author],
                "status": "running",
                "elapsed_ms": int((time.time() - started) * 1000),
            })
        for part in (event.get("content") or {}).get("parts", []):
            name = (part.get("functionCall") or {}).get("name")
            if name:
                store.add_timeline(invoice_id, "agent.tool_call", name)
        if time.time() - started > timeout_s:
            store.add_timeline(invoice_id, "agent.timeout",
                               f"exceeded {timeout_s:.0f}s, escalating")
            break

    final = agent.get_session(user_id="backend", session_id=session_id)
    state = final.get("state", {}) or {}
    elapsed_ms = int((time.time() - started) * 1000)

    result = {
        "matching_evidence": state.get("matching_evidence"),
        "matching_finding": _as_dict(state.get("matching_finding")),
        "policy_evidence": state.get("policy_evidence"),
        "policy_verdict": _as_dict(state.get("policy_verdict")),
        "elapsed_ms": elapsed_ms,
        "session_id": session_id,
    }
    store.add_timeline(invoice_id, "agent.completed", f"{elapsed_ms} ms")
    return result
