"""FastAPI app. Thin routes over pipeline, store and bq."""
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import bq, config, gate, pipeline, store

app = FastAPI(title="P2P autonomous back office", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bounded on purpose. The agent calls are the slow part and Agent Engine will
# happily rate-limit you if the batch replay fans out unbounded.
_pool = ThreadPoolExecutor(max_workers=4)

Mode = Literal["fixture", "docai"]


class Decision(BaseModel):
    actor: str = "ap.reviewer"
    note: Optional[str] = None
    override_reason: Optional[str] = None


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "settings": config.describe()}


@app.post("/api/invoices/{invoice_id}/ingest")
def ingest(invoice_id: str, tasks: BackgroundTasks,
           mode: Mode = "fixture") -> Dict[str, Any]:
    """Start the pipeline. Returns immediately; watch Firestore for progress."""
    if not bq.invoice_header(invoice_id):
        raise HTTPException(404, f"{invoice_id} not found in invoices_inbox")
    tasks.add_task(pipeline.process, invoice_id, mode)
    return {"invoice_id": invoice_id, "status": "accepted", "mode": mode}


@app.post("/api/invoices/{invoice_id}/run")
def run_sync(invoice_id: str, mode: Mode = "fixture") -> Dict[str, Any]:
    """Run synchronously and return the outcome. Handy for debugging one case."""
    return pipeline.process(invoice_id, mode)


@app.post("/api/batch/replay")
def replay(tasks: BackgroundTasks, limit: int = Query(100, ge=1, le=500),
           mode: Mode = "fixture", reset: bool = False) -> Dict[str, Any]:
    """Process many invoices. This is the demo's opening move."""
    if reset:
        store.clear_all()
    ids = bq.pending_invoice_ids(limit)

    def _run_all() -> None:
        list(_pool.map(lambda i: pipeline.process(i, mode), ids))

    tasks.add_task(_run_all)
    return {"queued": len(ids), "mode": mode, "reset": reset}


@app.get("/api/invoices")
def list_invoices(status: Optional[str] = None,
                  route: Optional[str] = None) -> Dict[str, Any]:
    cases = store.list_cases()
    if status:
        cases = [c for c in cases if c.get("status") == status]
    if route:
        cases = [c for c in cases if (c.get("decision") or {}).get("route") == route]
    cases.sort(key=lambda c: c.get("updated_at") or "", reverse=True)
    return {"count": len(cases), "invoices": [_summarise(c) for c in cases]}


def _summarise(case: Dict[str, Any]) -> Dict[str, Any]:
    header = case.get("header") or {}
    decision = case.get("decision") or {}
    return {
        "invoice_id": case.get("invoice_id"),
        "status": case.get("status"),
        "vendor": header.get("vendor_name_raw"),
        "po_ref": header.get("po_ref"),
        "currency": header.get("currency"),
        "total": header.get("total"),
        "channel": header.get("source_channel"),
        "route": decision.get("route"),
        "action": decision.get("action"),
        "reasons": decision.get("reasons") or [],
        "variance_cause": decision.get("variance_cause"),
        "citation": decision.get("citation"),
        "ms_total": (case.get("metrics") or {}).get("ms_total"),
        "updated_at": case.get("updated_at"),
    }


@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: str) -> Dict[str, Any]:
    """Everything the case-detail screen needs, in one call."""
    case = store.get_case(invoice_id)
    if not case:
        raise HTTPException(404, f"No case for {invoice_id}. Ingest it first.")
    po_ref = (case.get("header") or {}).get("po_ref")
    case["invoice_lines"] = bq.invoice_lines(invoice_id)
    case["po_and_grn"] = bq.po_and_grn(po_ref) if po_ref else {}
    return case


@app.post("/api/invoices/{invoice_id}/approve")
def approve(invoice_id: str, body: Decision) -> Dict[str, Any]:
    case = store.get_case(invoice_id)
    if not case:
        raise HTTPException(404, f"No case for {invoice_id}")
    header = case.get("header") or {}
    decision = case.get("decision") or {}
    doc_no = f"AP{invoice_id.split('-')[-1]}"

    bq.insert_erp_posting(
        invoice_id=invoice_id, po_ref=header.get("po_ref"),
        vendor_id=None, currency=header.get("currency"),
        amount=header.get("total"), gl_account="500100 Purchases",
        cost_center=None, posted_by=body.actor, doc_no=doc_no,
    )
    bq.insert_decision(
        invoice_id=invoice_id, actor=body.actor, agent="human",
        action="approved", route="post", reason=body.note or "approved by reviewer",
        citation=decision.get("citation") or "", confidence=1.0,
        latency_ms=None, tokens=None, cost_usd=None, payload=None,
    )
    store.patch(invoice_id, erp={"doc_no": doc_no, "posted_by": body.actor})
    store.set_status(invoice_id, "posted", "action.executed",
                     f"ERP document {doc_no}")
    return {"invoice_id": invoice_id, "status": "posted", "doc_no": doc_no}


@app.post("/api/invoices/{invoice_id}/reject")
def reject(invoice_id: str, body: Decision) -> Dict[str, Any]:
    """Rejections are the learning loop's input, so the reason is required."""
    if not store.get_case(invoice_id):
        raise HTTPException(404, f"No case for {invoice_id}")
    if not body.override_reason:
        raise HTTPException(422, "override_reason is required on a rejection")
    bq.insert_decision(
        invoice_id=invoice_id, actor=body.actor, agent="human",
        action="rejected", route="hold", reason=body.override_reason,
        citation="", confidence=1.0, latency_ms=None, tokens=None,
        cost_usd=None, payload=None,
    )
    store.patch(invoice_id, override={"reason": body.override_reason,
                                      "actor": body.actor})
    store.set_status(invoice_id, "rejected", "human.overrode", body.override_reason)
    return {"invoice_id": invoice_id, "status": "rejected"}


@app.get("/api/metrics")
def metrics() -> Dict[str, Any]:
    cases = store.list_cases()
    done = [c for c in cases
            if c.get("status") in ("posted", "posted_pending_approval",
                                   "awaiting_approval", "rejected")]
    touchless = [c for c in done if (c.get("decision") or {}).get("route") == "post"]
    escalated = [c for c in done if (c.get("decision") or {}).get("route") == "hold"]
    agented = [c for c in done if (c.get("metrics") or {}).get("agent_ms")]
    times = [(c.get("metrics") or {}).get("ms_total") or 0 for c in done]

    n = len(done) or 1
    causes: Dict[str, int] = {}
    for c in escalated:
        for r in (c.get("decision") or {}).get("reasons") or ["unspecified"]:
            causes[r] = causes.get(r, 0) + 1

    return {
        "processed": len(done),
        "in_flight": len(cases) - len(done),
        "touchless": len(touchless),
        "escalated": len(escalated),
        "touchless_rate": round(len(touchless) / n, 4),
        "agent_invoked": len(agented),
        "avg_cycle_ms": round(sum(times) / n),
        "cost_per_invoice_usd": 2.00,
        "manual_cost_per_invoice_usd": config.MANUAL_COST_PER_INVOICE,
        "cost_saved_usd": round(
            len(done) * (config.MANUAL_COST_PER_INVOICE - 2.00), 2),
        "hours_saved": round(
            len(touchless) * config.MANUAL_MINUTES_PER_INVOICE / 60.0, 1),
        "exceptions_by_reason": dict(
            sorted(causes.items(), key=lambda kv: -kv[1])),
    }


@app.get("/api/alerts")
def alerts() -> Dict[str, Any]:
    dups = bq.duplicate_alerts()
    banks = bq.bank_change_alerts()
    return {
        "duplicates": dups,
        "bank_changes": banks,
        "total": len(dups) + len(banks),
        "value_at_risk": round(
            sum(float(d.get("total") or 0) for d in dups + banks), 2),
    }


@app.get("/api/checks/{invoice_id}")
def checks(invoice_id: str) -> List[Dict[str, Any]]:
    """Raw check rows, for the case-detail match table."""
    return [{**c, "label": gate.label(c["check_name"])}
            for c in bq.match_checks(invoice_id)]
