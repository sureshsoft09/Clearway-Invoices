"""Run the pipeline locally against one invoice. No deployment needed.

    python run_local.py INV-1010

Use this for every iteration. Deploy to Agent Engine only when the output is
already what you want - each deploy costs you ten minutes you do not have.
"""
import asyncio
import json
import sys

from google.adk.runners import InMemoryRunner
from google.genai import types

from p2p_agent.agent import root_agent

STATE_KEYS = ("matching_evidence", "matching_finding", "policy_evidence", "policy_verdict")


async def main(invoice_id: str) -> None:
    runner = InMemoryRunner(agent=root_agent, app_name="p2p")
    session = await runner.session_service.create_session(app_name="p2p", user_id="dev")
    msg = types.Content(
        role="user",
        parts=[types.Part(text=f"Resolve the exception on invoice {invoice_id}.")],
    )

    async for event in runner.run_async(
        user_id="dev", session_id=session.id, new_message=msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    print(f"  [tool] {part.function_call.name}"
                          f"({dict(part.function_call.args)})")
        if event.is_final_response():
            print(f"  [{event.author}] done")

    final = await runner.session_service.get_session(
        app_name="p2p", user_id="dev", session_id=session.id
    )
    print("\n" + "=" * 70)
    for key in STATE_KEYS:
        val = final.state.get(key)
        if val is None:
            continue
        print(f"\n### {key}")
        print(json.dumps(val, indent=2) if isinstance(val, (dict, list)) else val)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "INV-1010"))
