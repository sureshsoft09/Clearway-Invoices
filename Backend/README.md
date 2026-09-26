# P2P backend

FastAPI. Reads the deterministic match from BigQuery, calls the Agent Engine
pipeline for exceptions, writes live case state to Firestore for the UI.

## Run
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    copy .env.example .env      # set AGENT_ENGINE_RESOURCE
    uvicorn app.main:app --reload --port 8080

Docs at http://localhost:8080/docs

## Endpoints
    POST /api/invoices/{id}/ingest?mode=fixture|docai   start the pipeline
    POST /api/batch/replay?limit=100                    run many, for the demo
    GET  /api/invoices                                  list with status
    GET  /api/invoices/{id}                             full case file
    POST /api/invoices/{id}/approve                     post to mock ERP
    POST /api/invoices/{id}/reject                      capture override
    GET  /api/metrics                                   touchless rate, cost, cycle
    GET  /api/alerts                                     duplicates and bank changes

## Why the frontend should not poll
Every stage writes to `cases/{invoice_id}` in Firestore. Subscribe with onSnapshot
and the pipeline board updates itself. The REST list endpoint exists for debugging
and for the metrics panel, not for the live view.

## Modes
`fixture` loads the pre-extracted JSON and skips Document AI: fast, free, and it
works when the processor is misbehaving. `docai` runs the real processor against the
PDF in GCS. Demo two or three invoices in docai mode and the bulk in fixture mode.
