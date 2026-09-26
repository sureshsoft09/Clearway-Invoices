"""Root agent: matching, then policy.

Deliberately a SequentialAgent rather than an LLM supervisor. For the exception
cases this pipeline handles, the order is never in doubt - you establish the facts,
then you rule on them. A routing LLM would add a model call, latency and a failure
mode without deciding anything useful.

Add risk_agent and resolution_agent to sub_agents when they land; the shape does not
change. If you later need genuine routing (for example to skip policy when the
finding needs no contract check), swap this for an LlmAgent with the sub_agents
wrapped in AgentTool.
"""
from google.adk.agents import SequentialAgent

from .sub_agents import matching_agent, policy_agent

root_agent = SequentialAgent(
    name="p2p_exception_pipeline",
    description=(
        "Resolves accounts payable exceptions: explains a three-way match variance, "
        "then rules on whether the contract permits it, with a clause citation."
    ),
    sub_agents=[matching_agent, policy_agent],
)
