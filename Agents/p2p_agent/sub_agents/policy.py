"""Policy agent - rules on whether the contract permits the invoiced treatment.

Same two-stage shape as matching, and for the same reason: VertexAiSearchTool is a
tool, so the agent holding it cannot also carry an output_schema.

The value of this agent is the citation, not the verdict. A verdict without a clause
quote is worthless in an audit, so evidence_found=false is a perfectly good answer.
"""
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import VertexAiSearchTool

from .. import config
from ..schemas import PolicyVerdict

contracts_search = VertexAiSearchTool(data_store_id=config.SEARCH_DATA_STORE_ID)

SEARCH_PROMPT = """
You are a contracts analyst searching a corpus of supply agreements, rate cards and
transport contracts.

You will be given a matching finding that includes a policy_question. Search the
corpus to answer exactly that question for the vendor and contract in play.

Procedure:
1. Search with the substantive terms, not the whole question. Good queries look like
   "price escalation cap", "freight invoiced separately", "unit of measure cases",
   "short shipment quantity received", "bank account change notification".
2. If the first search returns nothing on point, reformulate once with synonyms from
   contract language - "escalation" also appears as "price revision" or "indexation".
3. Prefer the contract belonging to the vendor on the invoice. If a clause comes from
   a different vendor's contract, it does not apply - say so rather than using it.

Report back, in plain text:
- The clause number and the document it came from.
- The verbatim sentence that decides the matter, in quotation marks. Copy it exactly;
  do not tidy the wording.
- The numeric ceiling or condition the clause imposes, if any.
- Whether you found nothing relevant. Say that plainly. Never construct a clause
  number, never paraphrase a clause you did not retrieve, and never infer a cap from
  what would be commercially reasonable.
"""

DECIDE_PROMPT = """
You are issuing a contractual ruling that will be attached to a payment decision and
may be reviewed by an auditor.

Matching finding:
{matching_finding}

Contract search result:
{policy_evidence}

Rules:
- If the search result contains no clause on point, set evidence_found to false,
  permitted to false, and say in reasoning that the corpus does not cover it. Leave
  clause_reference, quote and contract_id empty. An escalation with an honest "no
  clause found" is correct; an invented clause is a failure.
- When a numeric ceiling applies, compare it against the observed value and populate
  limit_applied and observed_value with both figures. Permitted is true only when the
  observed value is within the ceiling.
- quote must be copied verbatim from the search result and stay under 40 words.
- clause_reference is the number alone, for example 7.2, not the surrounding text.
- confidence reflects how squarely the clause addresses the facts. A clause that is
  merely adjacent scores low.
"""

policy_search = LlmAgent(
    name="policy_search",
    model=config.MODEL_REASONING,
    description="Retrieves the governing clause from the contract corpus.",
    instruction=SEARCH_PROMPT,
    tools=[contracts_search],
    output_key="policy_evidence",
)

policy_decide = LlmAgent(
    name="policy_decide",
    model=config.MODEL_FAST,
    description="Issues a typed PolicyVerdict with a clause citation.",
    instruction=DECIDE_PROMPT,
    output_schema=PolicyVerdict,
    output_key="policy_verdict",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

policy_agent = SequentialAgent(
    name="policy_agent",
    description="Rules on contractual permissibility, with a citation.",
    sub_agents=[policy_search, policy_decide],
)
