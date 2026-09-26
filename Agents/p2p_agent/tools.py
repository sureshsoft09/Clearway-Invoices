"""Tools the agents call. Every one returns plain JSON-serialisable dicts.

Keep these read-only. Posting to the ERP is the backend's job, behind the
human approval gate - an agent must never be able to move money.
"""
from typing import Any, Dict, List

from google.cloud import bigquery

from . import config

_client: bigquery.Client | None = None


def _bq() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=config.PROJECT)
    return _client


def _rows(sql: str, params: List[bigquery.ScalarQueryParameter]) -> List[Dict[str, Any]]:
    job = _bq().query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params))
    out = []
    for r in job.result():
        d = dict(r.items())
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
            elif isinstance(v, list):
                d[k] = [str(x) for x in v]
            elif v is not None and not isinstance(v, (str, int, float, bool)):
                d[k] = str(v)
        out.append(d)
    return out


def get_case(invoice_id: str) -> Dict[str, Any]:
    """Get the deterministic match result for one invoice.

    Returns the routing hint, which checks failed, and the header facts. Call this
    first for any invoice - it tells you what is actually broken so you do not have
    to rediscover it.

    Args:
        invoice_id: Invoice identifier, for example 'INV-1042'.
    """
    p = [bigquery.ScalarQueryParameter("id", "STRING", invoice_id)]
    summary = _rows(
        f"SELECT * FROM {config.fq('v_match_summary')} WHERE invoice_id = @id", p
    )
    if not summary:
        return {"error": f"No case found for {invoice_id}"}
    checks = _rows(
        f"""SELECT check_name, severity, status, expected, actual
            FROM {config.fq('v_match_checks')}
            WHERE invoice_id = @id AND status != 'na'
            ORDER BY severity, check_name""",
        p,
    )
    lines = _rows(
        f"""SELECT line_no, item_code, item_desc, uom, qty, unit_price, line_total
            FROM {config.fq('invoice_lines')} WHERE invoice_id = @id ORDER BY line_no""",
        p,
    )
    return {
        "summary": summary[0],
        "checks": checks,
        "failed_checks": [c for c in checks if c["status"] == "fail"],
        "invoice_lines": lines,
    }


def get_po_and_grn(po_ref: str) -> Dict[str, Any]:
    """Get purchase order lines and matching goods receipt lines.

    Use this to establish what was ordered versus what was physically received.
    The GRN note often contains the receiving clerk's explanation for a shortfall.

    Args:
        po_ref: Purchase order number, for example 'PO-7409'.
    """
    p = [bigquery.ScalarQueryParameter("po", "STRING", po_ref)]
    po = _rows(
        f"""SELECT po_line, item_code, item_desc, uom, qty_ordered, unit_price,
                   currency, line_total, po_date, buyer, status, contract_id
            FROM {config.fq('purchase_orders')} WHERE po_id = @po ORDER BY po_line""",
        p,
    )
    grn = _rows(
        f"""SELECT grn_id, po_line, item_code, qty_received, uom, received_on,
                   warehouse, note
            FROM {config.fq('goods_receipts')} WHERE po_id = @po ORDER BY po_line""",
        p,
    )
    return {"po_ref": po_ref, "po_lines": po, "goods_receipts": grn,
            "grn_exists": bool(grn)}


def get_vendor_terms(vendor_id: str) -> Dict[str, Any]:
    """Get the vendor master record, including the contract id and escalation cap.

    Use the contract id to know which contract the Policy step should search.

    Args:
        vendor_id: Vendor identifier, for example 'V001'.
    """
    rows = _rows(
        f"""SELECT vendor_id, vendor_name, currency, payment_terms, contract_id,
                   escalation_cap_pct, status
            FROM {config.fq('vendor_master')} WHERE vendor_id = @v""",
        [bigquery.ScalarQueryParameter("v", "STRING", vendor_id)],
    )
    return rows[0] if rows else {"error": f"Vendor {vendor_id} not in master"}


def get_vendor_price_history(vendor_id: str, item_code: str) -> Dict[str, Any]:
    """Get the unit prices this vendor has previously charged for an item.

    Use this to judge whether a price change is a one-off or an established trend.

    Args:
        vendor_id: Vendor identifier, for example 'V001'.
        item_code: Item code, for example 'ACM-4410'.
    """
    rows = _rows(
        f"""SELECT po_date, unit_price, qty_ordered, po_id
            FROM {config.fq('purchase_orders')}
            WHERE vendor_id = @v AND item_code = @i
            ORDER BY po_date DESC LIMIT 12""",
        [bigquery.ScalarQueryParameter("v", "STRING", vendor_id),
         bigquery.ScalarQueryParameter("i", "STRING", item_code)],
    )
    prices = [r["unit_price"] for r in rows if r.get("unit_price") is not None]
    return {
        "vendor_id": vendor_id,
        "item_code": item_code,
        "history": rows,
        "median_unit_price": sorted(prices)[len(prices) // 2] if prices else None,
    }
