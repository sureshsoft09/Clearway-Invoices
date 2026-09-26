"""Deploy the pipeline to Vertex AI Agent Engine.

    python deploy.py            # create, prints the resource name
    python deploy.py <res_name> # update an existing deployment

Runs as SERVICE_ACCOUNT from .env when set, otherwise as the default Reasoning
Engine service agent. Prefer the explicit service account: the default agent is
only created on your first deployment, so you cannot grant it roles up front,
and its first tool call fails.

Save the printed resource name into .env as AGENT_ENGINE_RESOURCE.
"""
import sys

import vertexai
from vertexai import agent_engines
from vertexai.preview import reasoning_engines

from p2p_agent import config
from p2p_agent.agent import root_agent

REQUIREMENTS = [
    "google-adk>=1.0.0",
    "google-cloud-aiplatform[adk,agent_engines]>=1.95.0",
    "google-cloud-bigquery>=3.25.0",
    "pydantic>=2.6.0,<2.8.0",
    "python-dotenv>=1.0.0",
]

# Agent Engine injects project, location and the Vertex AI switch itself and
# rejects the deployment if you pass them - hence the filter. Everything else the
# agent needs at runtime must be passed here, because .env is not shipped with the
# package. If a new name turns out to be reserved, add it to RESERVED.
RESERVED = {
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_GENAI_USE_VERTEXAI",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "PORT",
}

ENV_VARS = {k: v for k, v in {
    "BQ_DATASET": config.DATASET,
    "SEARCH_DATA_STORE_ID": config.SEARCH_DATA_STORE_ID,
    "MODEL_REASONING": config.MODEL_REASONING,
    "MODEL_FAST": config.MODEL_FAST,
}.items() if k not in RESERVED and v}


def main() -> None:
    for name, val in (("GOOGLE_CLOUD_PROJECT", config.PROJECT),
                      ("STAGING_BUCKET", config.STAGING_BUCKET),
                      ("SEARCH_DATA_STORE_ID", config.SEARCH_DATA_STORE_ID)):
        if not val:
            raise SystemExit(f"{name} is not set. Copy .env.example to .env first.")

    vertexai.init(project=config.PROJECT, location=config.LOCATION,
                  staging_bucket=config.STAGING_BUCKET)
    app = reasoning_engines.AdkApp(agent=root_agent,
                                   enable_tracing=config.ENABLE_TRACING)

    kwargs = dict(
        agent_engine=app,
        requirements=REQUIREMENTS,
        extra_packages=["p2p_agent"],
        env_vars=ENV_VARS,
    )
    if config.SERVICE_ACCOUNT:
        kwargs["service_account"] = config.SERVICE_ACCOUNT
        print(f"Runtime identity: {config.SERVICE_ACCOUNT}")
    else:
        print("Runtime identity: default Reasoning Engine service agent")
    print(f"Settings: {config.describe()}")
    print(f"Runtime env vars: {sorted(ENV_VARS)}")

    try:
        if len(sys.argv) > 1:
            remote = agent_engines.get(sys.argv[1]).update(**kwargs)
        else:
            remote = agent_engines.create(
                display_name="invoice-process-agents",
                description=("AP exception resolution: matching then policy, "
                             "with clause citations."),
                **kwargs,
            )
    except TypeError as exc:
        if "service_account" in str(exc):
            raise SystemExit(
                "This google-cloud-aiplatform version does not accept "
                "service_account. Upgrade it, or clear SERVICE_ACCOUNT in .env "
                "and grant roles to the default service agent after the first "
                "deployment creates it."
            ) from exc
        raise

    print("\nRESOURCE NAME:", remote.resource_name)
    print("Add this to .env as AGENT_ENGINE_RESOURCE")


if __name__ == "__main__":
    main()
