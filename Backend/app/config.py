"""Settings. override=True for the same reason as the agents package: this machine
has GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION pre-set to corporate values in
the shell, and python-dotenv leaves existing variables alone by default.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
DATASET = os.environ.get("BQ_DATASET", "p2p")

AGENT_ENGINE_RESOURCE = os.environ.get("AGENT_ENGINE_RESOURCE", "")
DOCAI_LOCATION = os.environ.get("DOCAI_LOCATION", "us")
DOCAI_PROCESSOR_ID = os.environ.get("DOCAI_PROCESSOR_ID", "")
INVOICES_BUCKET = os.environ.get("INVOICES_BUCKET", "")

# Relative values resolve against Src/Backend, so uvicorn works from any cwd.
_fixtures = Path(os.environ.get("FIXTURES_DIR") or "fixtures")
FIXTURES_DIR = _fixtures if _fixtures.is_absolute() else (BACKEND_DIR / _fixtures)

CORS_ORIGINS = [o.strip() for o in
                os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
                if o.strip()]

MANUAL_COST_PER_INVOICE = float(os.environ.get("MANUAL_COST_PER_INVOICE", "13.50"))
MANUAL_MINUTES_PER_INVOICE = float(os.environ.get("MANUAL_MINUTES_PER_INVOICE", "9"))

if not PROJECT:
    raise RuntimeError(f"GOOGLE_CLOUD_PROJECT is empty. Set it in {BACKEND_DIR / '.env'}")
if LOCATION == "global":
    raise RuntimeError("GOOGLE_CLOUD_LOCATION is 'global', which Vertex AI rejects. "
                       "Set us-central1.")


def fq(table: str) -> str:
    return f"`{PROJECT}.{DATASET}.{table}`"


def describe() -> str:
    return (f"project={PROJECT} dataset={DATASET} "
            f"agent={'set' if AGENT_ENGINE_RESOURCE else 'MISSING'} "
            f"docai={'set' if DOCAI_PROCESSOR_ID else 'fixture-only'} "
            f"fixtures={FIXTURES_DIR} ({'found' if FIXTURES_DIR.exists() else 'MISSING'})")
