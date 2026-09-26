# P2P exception agents (ADK -> Agent Engine)

## Layout
    p2p_agent/
      agent.py               root_agent, a SequentialAgent
      config.py              env-driven settings
      schemas.py             MatchingFinding, PolicyVerdict
      tools.py               read-only BigQuery tools
      sub_agents/
        matching.py          investigate -> conclude
        policy.py            search -> decide
    run_local.py             iterate here
    deploy.py                Agent Engine deploy

## Setup
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    copy .env.example .env      # then edit SEARCH_DATA_STORE_ID
    gcloud auth application-default login

## Iterate
    python run_local.py INV-1010     # uom difference, should reconcile on value
    python run_local.py INV-1039     # +8.46% uplift, should be refused on the 5% cap
    adk web                          # browser UI, inspect state and traces

## Deploy
    python deploy.py

## Why each agent is split in two
ADK raises a ValueError if an agent has both `tools` and an `output_schema`. So each
logical agent is a SequentialAgent of a tool-using stage and a typing stage. The
first writes plain text to session state via `output_key`; the second reads it through
`{placeholder}` interpolation in its instruction and emits the pydantic model.

## Reading the output
Final session state carries four keys:
- `matching_evidence`  - plain text evidence brief
- `matching_finding`   - MatchingFinding
- `policy_evidence`    - plain text clause search result
- `policy_verdict`     - PolicyVerdict

The backend decides from `matching_finding.recommended_action` and
`policy_verdict.permitted`. Post touchless only when policy permits it; anything with
`evidence_found=false` goes to a human.

## Gotchas
- `SEARCH_DATA_STORE_ID` must be the full resource path copied from the AI
  Applications console. Hand-assembling it is the most common failure here.
- Confirm your model ids exist in your region before changing `.env`.
- Tools are read-only by design. Never give an agent write access to the ERP - the
  backend posts, behind the human gate.
