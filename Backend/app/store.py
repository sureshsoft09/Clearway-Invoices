"""Firestore case store. This is what the UI subscribes to.

One document per invoice at cases/{invoice_id}. Every pipeline stage patches it, so
the frontend gets a live view from onSnapshot without any polling or websockets.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List

from google.cloud import firestore

from . import config

COLLECTION = "cases"
_db: firestore.Client | None = None


def db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=config.PROJECT)
    return _db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def doc(invoice_id: str):
    return db().collection(COLLECTION).document(invoice_id)


def create_case(invoice_id: str, header: Dict[str, Any]) -> None:
    doc(invoice_id).set({
        "invoice_id": invoice_id,
        "status": "received",
        "route": None,
        "header": header,
        "extracted": None,
        "match": None,
        "risk": None,
        "agent_trace": [],
        "decision": None,
        "timeline": [{"ts": _now(), "event": "invoice.received",
                      "detail": f"via {header.get('source_channel', 'unknown')}"}],
        "metrics": {"ms_total": 0},
        "created_at": _now(),
        "updated_at": _now(),
    })


def patch(invoice_id: str, **fields: Any) -> None:
    doc(invoice_id).update({**fields, "updated_at": _now()})


def set_status(invoice_id: str, status: str, event: str, detail: str = "") -> None:
    doc(invoice_id).update({
        "status": status,
        "updated_at": _now(),
        "timeline": firestore.ArrayUnion(
            [{"ts": _now(), "event": event, "detail": detail}]),
    })


def add_timeline(invoice_id: str, event: str, detail: str = "") -> None:
    doc(invoice_id).update({
        "updated_at": _now(),
        "timeline": firestore.ArrayUnion(
            [{"ts": _now(), "event": event, "detail": detail}]),
    })


def add_agent_step(invoice_id: str, entry: Dict[str, Any]) -> None:
    """Append one agent step as it happens, so the UI timeline fills in live."""
    doc(invoice_id).update({
        "updated_at": _now(),
        "agent_trace": firestore.ArrayUnion([{"ts": _now(), **entry}]),
    })


def get_case(invoice_id: str) -> Dict[str, Any] | None:
    snap = doc(invoice_id).get()
    return snap.to_dict() if snap.exists else None


def list_cases(limit: int = 200) -> List[Dict[str, Any]]:
    return [s.to_dict() for s in
            db().collection(COLLECTION).limit(limit).stream()]


def clear_all() -> int:
    """Wipe every case. Use between demo runs, never in anger."""
    n = 0
    for snap in db().collection(COLLECTION).stream():
        snap.reference.delete()
        n += 1
    return n
