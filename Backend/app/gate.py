"""The decision gate.

Deterministic code, deliberately. The agents supply findings; this decides what
happens to the money. A model must never be able to grant itself authority to post,
so nothing here asks a model anything.
"""
from typing import Any, Dict, List, Tuple

MIN_MATCH_CONFIDENCE = 0.70
MIN_POLICY_CONFIDENCE = 0.60
POSTABLE_ACTIONS = {"post_as_invoiced", "post_partial"}

CHECK_LABELS = {
    "vendor_resolved": "Vendor not in master",
    "po_exists": "No valid PO",
    "po_belongs_to_vendor": "PO belongs to another vendor",
    "bank_account_match": "Bank account differs from master",
    "bank_change_verified": "Unverified bank change",
    "not_duplicate": "Possible duplicate",
    "qty_within_grn": "Billed above quantity received",
    "qty_matches_po": "Quantity differs from PO",
    "unit_price_matches_po": "Unit price differs from PO",
    "uom_matches_po": "Unit of measure differs",
    "all_lines_on_po": "Line not on PO",
    "currency_matches_po": "Currency differs from PO",
    "totals_recompute": "Totals do not recompute",
    "extraction_confidence": "Low extraction confidence",
}


def label(check: str) -> str:
    return CHECK_LABELS.get(check, check.replace("_", " "))


def needs_agent(summary: Dict[str, Any]) -> bool:
    return summary.get("route_hint") == "agent_review"


def decide(summary: Dict[str, Any],
           agent_result: Dict[str, Any] | None) -> Tuple[str, List[str], str]:
    """Return (route, reasons, action).

    route  - "post" or "hold"
    action - what to do with the invoice, for the UI and the ledger
    """
    hint = summary.get("route_hint")

    if hint == "escalate":
        return ("hold",
                [label(c) for c in (summary.get("hard_failed") or [])],
                "escalate_to_human")

    if hint == "touchless":
        return ("post", [], "post_as_invoiced")

    # agent_review
    if not agent_result:
        return ("hold", ["Agent did not return a result"], "escalate_to_human")

    finding = agent_result.get("matching_finding") or {}
    verdict = agent_result.get("policy_verdict") or {}
    reasons: List[str] = []

    action = finding.get("recommended_action")
    if action not in POSTABLE_ACTIONS:
        reasons.append(f"Agent recommends {str(action).replace('_', ' ')}")
    if float(finding.get("confidence") or 0) < MIN_MATCH_CONFIDENCE:
        reasons.append("Variance explanation below confidence threshold")
    if finding.get("variance_cause") == "unexplained":
        reasons.append("Variance not explained")

    if finding.get("needs_policy_check", True):
        if not verdict.get("evidence_found"):
            reasons.append("No contract clause found to permit this")
        elif not verdict.get("permitted"):
            ref = verdict.get("clause_reference")
            reasons.append(f"Not permitted by clause {ref}" if ref
                           else "Not permitted by contract")
        elif float(verdict.get("confidence") or 0) < MIN_POLICY_CONFIDENCE:
            reasons.append("Clause match too weak to rely on")

    if reasons:
        return ("hold", reasons, "escalate_to_human")
    return ("post", [], action)


def citation(agent_result: Dict[str, Any] | None) -> str:
    """One-line citation for the ledger and the UI."""
    verdict = (agent_result or {}).get("policy_verdict") or {}
    if not verdict.get("evidence_found"):
        return ""
    parts = [p for p in (verdict.get("contract_id"),
                         f"clause {verdict['clause_reference']}"
                         if verdict.get("clause_reference") else None) if p]
    return " ".join(parts)
