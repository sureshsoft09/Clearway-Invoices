"""Two extraction paths.

fixture: load the pre-extracted JSON. Fast, free, deterministic. Use it for the bulk
         run and as the fallback if Document AI is unavailable.
docai:   run the real Invoice Parser against the PDF in GCS. Use it on two or three
         invoices in the demo so the real extraction is visible.

Both return the same shape, so nothing downstream knows or cares which ran.
"""
import json
from typing import Any, Dict

from . import config


def load_fixture(invoice_id: str) -> Dict[str, Any]:
    path = config.FIXTURES_DIR / f"{invoice_id}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No fixture at {path}. Set FIXTURES_DIR in .env to the folder holding "
            f"the invoice JSONs.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["extracted"]["_extraction_mode"] = "fixture"
    return payload["extracted"]


def docai_extract(invoice_id: str, gcs_uri: str) -> Dict[str, Any]:
    """Run Document AI Invoice Parser on a PDF already in GCS."""
    if not config.DOCAI_PROCESSOR_ID:
        raise RuntimeError(
            "DOCAI_PROCESSOR_ID is not set. Use mode=fixture, or create an Invoice "
            "Parser processor and put its id in .env.")
    from google.api_core.client_options import ClientOptions
    from google.cloud import documentai

    opts = ClientOptions(
        api_endpoint=f"{config.DOCAI_LOCATION}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = client.processor_path(config.PROJECT, config.DOCAI_LOCATION,
                                config.DOCAI_PROCESSOR_ID)
    result = client.process_document(
        request=documentai.ProcessRequest(
            name=name,
            gcs_document=documentai.GcsDocument(
                gcs_uri=gcs_uri, mime_type="application/pdf"),
        )
    )
    return _from_document(result.document, invoice_id)


# Document AI entity type -> our field name
_FIELDS = {
    "invoice_id": "invoice_no",
    "invoice_date": "invoice_date",
    "supplier_name": "vendor_name_raw",
    "purchase_order": "po_ref",
    "currency": "currency",
    "net_amount": "subtotal",
    "total_tax_amount": "tax",
    "total_amount": "total",
    "supplier_iban": "bank_account",
    "payment_terms": "payment_terms",
}
_LINE_FIELDS = {
    "line_item/product_code": "item_code",
    "line_item/description": "item_desc",
    "line_item/unit": "uom",
    "line_item/quantity": "qty",
    "line_item/unit_price": "unit_price",
    "line_item/amount": "line_total",
}


def _num(text: str) -> float:
    cleaned = "".join(c for c in (text or "") if c.isdigit() or c in ".-")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _from_document(document: Any, invoice_id: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"lines": [], "field_confidence": {},
                           "_extraction_mode": "docai"}
    for ent in document.entities:
        key = _FIELDS.get(ent.type_)
        if not key:
            continue
        raw = ent.mention_text
        out[key] = _num(raw) if key in ("subtotal", "tax", "total") else raw
        out["field_confidence"][key] = round(float(ent.confidence), 3)

    for n, ent in enumerate((e for e in document.entities
                             if e.type_ == "line_item"), start=1):
        line: Dict[str, Any] = {"line_no": n}
        for prop in ent.properties:
            key = _LINE_FIELDS.get(prop.type_)
            if not key:
                continue
            line[key] = (_num(prop.mention_text)
                         if key in ("qty", "unit_price", "line_total")
                         else prop.mention_text)
        out["lines"].append(line)

    confs = list(out["field_confidence"].values())
    out["field_confidence"]["_min"] = min(confs) if confs else 0.0
    return out
