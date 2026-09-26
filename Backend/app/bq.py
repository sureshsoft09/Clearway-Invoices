"""BigQuery access. Reads the match views, writes the audit ledger and mock ERP."""
from datetime import datetime, timezone
from typing import Any, Dict, List

from google.cloud import bigquery

from . import config

_client: bigquery.Client | None = None


def client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=config.PROJECT)
    return _client


def _jsonable(v: Any) -> Any:
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def rows(sql: str, params: List[bigquery.ScalarQueryParameter] | None = None
         ) -> List[Dict[str, Any]]:
    cfg = bigquery.QueryJobConfig(query_parameters=params or [])
    return [{k: _jsonable(v) for k, v in dict(r.items()).items()}
            for r in client().query(sql, job_config=cfg).result()]


def _id(invoice_id: str) -> List[bigquery.ScalarQueryParameter]:
    return [bigquery.ScalarQueryParameter("id", "STRING", invoice_id)]


def match_summary(invoice_id: str) -> Dict[str, Any] | None:
    r = rows(f"SELECT * FROM {config.fq('v_match_summary')} WHERE invoice_id = @id",
             _id(invoice_id))
    return r[0] if r else None


def match_checks(invoice_id: str) -> List[Dict[str, Any]]:
    return rows(
        f"""SELECT check_name, severity, status, expected, actual
            FROM {config.fq('v_match_checks')}
            WHERE invoice_id = @id AND status != 'na'
            ORDER BY CASE severity WHEN 'hard' THEN 0 WHEN 'soft' THEN 1 ELSE 2 END,
                     check_name""",
        _id(invoice_id))


def invoice_header(invoice_id: str) -> Dict[str, Any] | None:
    r = rows(f"SELECT * FROM {config.fq('invoices_inbox')} WHERE invoice_id = @id",
             _id(invoice_id))
    return r[0] if r else None


def invoice_lines(invoice_id: str) -> List[Dict[str, Any]]:
    return rows(
        f"""SELECT line_no, item_code, item_desc, uom, qty, unit_price, line_total
            FROM {config.fq('invoice_lines')} WHERE invoice_id = @id ORDER BY line_no""",
        _id(invoice_id))


def po_and_grn(po_ref: str) -> Dict[str, Any]:
    p = [bigquery.ScalarQueryParameter("po", "STRING", po_ref)]
    return {
        "po_lines": rows(
            f"""SELECT po_line, item_code, item_desc, uom, qty_ordered, unit_price,
                       currency, line_total, po_date, buyer, contract_id
                FROM {config.fq('purchase_orders')} WHERE po_id = @po ORDER BY po_line""", p),
        "goods_receipts": rows(
            f"""SELECT grn_id, po_line, item_code, qty_received, uom, received_on,
                       warehouse, note
                FROM {config.fq('goods_receipts')} WHERE po_id = @po ORDER BY po_line""", p),
    }


def pending_invoice_ids(limit: int = 100) -> List[str]:
    r = rows(f"""SELECT invoice_id FROM {config.fq('invoices_inbox')}
                 ORDER BY received_at LIMIT {int(limit)}""")
    return [x["invoice_id"] for x in r]


def duplicate_alerts() -> List[Dict[str, Any]]:
    return rows(
        f"""SELECT c.invoice_id, s.vendor_name_raw, s.po_ref, s.total, s.currency,
                   c.actual AS duplicate_of
            FROM {config.fq('v_match_checks')} c
            JOIN {config.fq('v_match_summary')} s USING (invoice_id)
            WHERE c.check_name = 'not_duplicate' AND c.status = 'fail'
            ORDER BY s.total DESC""")


def bank_change_alerts() -> List[Dict[str, Any]]:
    return rows(
        f"""SELECT s.invoice_id, s.vendor_name_raw, s.total, s.currency,
                   h.old_bank_account, h.new_bank_account,
                   CAST(h.changed_on AS STRING) AS changed_on,
                   h.changed_by, h.channel,
                   DATE_DIFF(s.invoice_date, h.changed_on, DAY) AS days_before_invoice
            FROM {config.fq('v_match_summary')} s
            JOIN {config.fq('invoices_inbox')} i USING (invoice_id)
            JOIN {config.fq('vendor_bank_history')} h
              ON h.new_bank_account = i.bank_account
            WHERE UPPER(CAST(h.verified AS STRING)) IN ('NO', 'FALSE')
            ORDER BY s.total DESC""")


def insert_decision(**kw: Any) -> None:
    row = {"ts": datetime.now(timezone.utc).isoformat(), **kw}
    errors = client().insert_rows_json(
        f"{config.PROJECT}.{config.DATASET}.decision_ledger", [row])
    if errors:
        raise RuntimeError(f"decision_ledger insert failed: {errors}")


def insert_erp_posting(**kw: Any) -> None:
    row = {"ts": datetime.now(timezone.utc).isoformat(), **kw}
    errors = client().insert_rows_json(
        f"{config.PROJECT}.{config.DATASET}.mock_erp_postings", [row])
    if errors:
        raise RuntimeError(f"mock_erp_postings insert failed: {errors}")
