"""Environment-driven settings. Nothing here should be hardcoded per developer.

override=True is deliberate and load-bearing. This machine already has
GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION set to corporate values in the
shell environment, and python-dotenv leaves pre-existing variables alone by
default. Without override, .env is silently ignored and every BigQuery and
Vertex AI call goes to the wrong project.

The path is resolved relative to this file rather than the working directory, so
running from the repo root, from Src/Agents, or from a test all behave the same.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "bitsomvertexproj")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
DATASET = os.environ.get("BQ_DATASET", "p2p")
SEARCH_DATA_STORE_ID = os.environ.get("SEARCH_DATA_STORE_ID", "")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "")
SERVICE_ACCOUNT = os.environ.get("SERVICE_ACCOUNT", "")
ENABLE_TRACING = os.environ.get("ENABLE_TRACING", "true").lower() == "true"

MODEL_REASONING = os.environ.get("MODEL_REASONING", "gemini-2.5-pro")
MODEL_FAST = os.environ.get("MODEL_FAST", "gemini-2.5-flash")

if not PROJECT:
    raise RuntimeError(
        f"GOOGLE_CLOUD_PROJECT is empty. Expected it in {ENV_PATH}, which "
        f"{'exists' if ENV_PATH.exists() else 'DOES NOT EXIST - copy .env.example to .env'}."
    )
if LOCATION == "global":
    raise RuntimeError(
        "GOOGLE_CLOUD_LOCATION is 'global', which Vertex AI model calls reject. "
        f"Set GOOGLE_CLOUD_LOCATION=us-central1 in {ENV_PATH}."
    )


def fq(table: str) -> str:
    """Fully qualified BigQuery table name."""
    return f"`{PROJECT}.{DATASET}.{table}`"


def describe() -> str:
    """One-line summary of resolved settings, for startup logs."""
    return (f"project={PROJECT} location={LOCATION} dataset={DATASET} "
            f"models={MODEL_REASONING}/{MODEL_FAST}")
