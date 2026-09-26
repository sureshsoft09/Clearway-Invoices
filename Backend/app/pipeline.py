"""Stage orchestration for one invoice.

Deliberately sequential and synchronous. Each stage patches Firestore before the
next begins, so the UI shows real progress and a failure leaves the case parked at
the stage that broke rather than silently disappearing.
"""
import time
import traceback
from typing import Any, Dict

from . import agent_client, bq, config, extraction, gate, store


def process(invoice_id: str, mode: str = "fixture") -> Dict[str, Any]:
    started = time.time()
    try:
        header = bq.invoice_header(invoice_id)
        if not header:
            raise ValueError(f"{invoice_id} not in invoices_inbox")

        if store.get_case(invoice_id) is None:
            store.create_case(invoice_id, header)

        # 1. extract
        store.set_status(invoice_id, "extracting", "extraction.started", mode)
        if mode == "docai":
            gcs_uri = f"gs://{config.INVOICES_BUCKET}/{invoice_id}.pdf"
            extracted = extraction.docai_extract(invoice_id, gcs_uri)
        else:
            extracted = extraction.load_fixture(invoice_id)
        store.patch(invoice_id, extracted=extracted)
        store.add_timeline(invoice_id, "invoice.extracted",
                           f"{len(extracted.get('lines', []))} lines, "
                           f"mode={extracted.get('_extraction_mode')}")

        # 2. deterministic three-way match
        store.set_status(invoice_id, "matching", "match.started",
                         "three-way match in BigQuery")
        summary = bq.match_summary(invoice_id)
        if not summary:
            raise ValueError(f"No match result for {invoice_id}. Are the views created?")
        checks = bq.match_checks(invoice_id)
        failed = [c for c in checks if c["status"] == "fail"]
        store.patch(invoice_id, match={
            "route_hint": summary.get("route_hint"),
            "hard_failed": summary.get("hard_failed") or [],
            "soft_failed": summary.get("soft_failed") or [],
            "evidence": summary.get("evidence") or [],
            "checks": checks,
            "po_ref": summary.get("po_ref"),
        })
        store.add_timeline(invoice_id, "invoice.matched",
                           f"{summary.get('route_hint')}, {len(failed)} check(s) failed")

        # 3. agents, only for genuine exceptions
        agent_result = None
        if gate.needs_agent(summary):
            store.set_status(invoice_id, "agent_review", "exception.raised",
                             ", ".join(gate.label(c) for c in
                                       (summary.get("soft_failed") or [])))
            agent_result = agent_client.run(invoice_id)
            store.patch(invoice_id, agent_result=agent_result)

        # 4. gate
        route, reasons, action = gate.decide(summary, agent_result)
        finding = (agent_result or {}).get("matching_finding") or {}
        verdict = (agent_result or {}).get("policy_verdict") or {}
        elapsed_ms = int((time.time() - started) * 1000)

        decision = {
            "route": route,
            "action": action,
            "reasons": reasons,
            "citation": gate.citation(agent_result),
            "variance_cause": finding.get("variance_cause"),
            "explanation": finding.get("explanation"),
            "clause_quote": verdict.get("quote"),
            "clause_reference": verdict.get("clause_reference"),
            "permitted": verdict.get("permitted"),
            "agent_ms": (agent_result or {}).get("elapsed_ms", 0),
        }
        status = "posted_pending_approval" if route == "post" else "awaiting_approval"
        store.patch(invoice_id, decision=decision,
                    metrics={"ms_total": elapsed_ms,
                             "agent_ms": decision["agent_ms"],
                             "touchless": route == "post"})
        store.set_status(invoice_id, status, "decision.made",
                         action if route == "post" else "; ".join(reasons))

        bq.insert_decision(
            invoice_id=invoice_id, actor="pipeline",
            agent="p2p_exception_pipeline" if agent_result else "deterministic",
            action=action, route=route, reason="; ".join(reasons) or "all checks pass",
            citation=decision["citation"],
            confidence=float(finding.get("confidence") or 1.0),
            latency_ms=elapsed_ms, tokens=None, cost_usd=None,
            payload=None,
        )
        return {"invoice_id": invoice_id, "route": route, "action": action,
                "reasons": reasons, "ms": elapsed_ms}

    except Exception as exc:  # keep the case visible with the real reason
        store.patch(invoice_id, error=f"{type(exc).__name__}: {exc}")
        store.set_status(invoice_id, "failed", "pipeline.error", str(exc)[:400])
        traceback.print_exc()
        return {"invoice_id": invoice_id, "route": "hold", "action": "failed",
                "reasons": [str(exc)], "ms": int((time.time() - started) * 1000)}
