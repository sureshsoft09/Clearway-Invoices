"""Call the deployed Agent Engine pipeline. This is also the reference for how
the backend should invoke it.

    python test_remote.py <resource_name> INV-1010

Pass the resource name printed by deploy.py, or set AGENT_ENGINE_RESOURCE in .env.
"""
import json
import os
import sys
import time

import vertexai
from vertexai import agent_engines

from p2p_agent import config

STATE_KEYS = ("matching_evidence", "matching_finding", "policy_evidence", "policy_verdict")


def main() -> None:
    resource = (sys.argv[1] if len(sys.argv) > 1
                else os.environ.get("AGENT_ENGINE_RESOURCE", ""))
    invoice_id = sys.argv[2] if len(sys.argv) > 2 else "INV-1010"
    if not resource:
        raise SystemExit("Pass the resource name, or set AGENT_ENGINE_RESOURCE in .env")

    vertexai.init(project=config.PROJECT, location=config.LOCATION)
    remote = agent_engines.get(resource)

    session = remote.create_session(user_id="backend")
    session_id = session["id"]
    started = time.time()

    for event in remote.stream_query(
        user_id="backend",
        session_id=session_id,
        message=f"Resolve the exception on invoice {invoice_id}.",
    ):
        author = event.get("author", "?")
        for part in (event.get("content") or {}).get("parts", []):
            if "functionCall" in part:
                print(f"  [tool] {part['functionCall'].get('name')}")
            elif part.get("text"):
                print(f"  [{author}] {part['text'][:120].strip()}")

    final = remote.get_session(user_id="backend", session_id=session_id)
    state = final.get("state", {})
    print(f"\n--- {invoice_id} in {time.time() - started:.1f}s ---")
    for key in STATE_KEYS:
        if key not in state:
            continue
        val = state[key]
        print(f"\n### {key}")
        print(json.dumps(val, indent=2) if isinstance(val, (dict, list)) else val)


if __name__ == "__main__":
    main()
