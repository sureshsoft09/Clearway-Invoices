"""Structured outputs. The backend and the UI both depend on these shapes."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

VarianceCause = Literal[
    "short_shipment",
    "overbilled_vs_receipt",
    "uom_difference",
    "price_escalation",
    "freight_billed_separately",
    "tax_or_rounding",
    "duplicate_submission",
    "wrong_po_referenced",
    "no_variance",
    "unexplained",
]


class MatchingFinding(BaseModel):
    """Why the numbers disagree, in terms an AP clerk would accept."""

    variance_cause: VarianceCause = Field(
        description="Single best explanation for the variance."
    )
    explanation: str = Field(
        description="Two or three sentences citing the specific quantities, prices and "
        "document numbers you compared. No hedging."
    )
    quantitative_basis: List[str] = Field(
        default_factory=list,
        description="One string per comparison made, e.g. "
        "'invoice 480 EA vs PO 500 EA vs GRN 480 EA'.",
    )
    value_reconciles: bool = Field(
        description="True when the extended line value matches the PO despite the "
        "quantity or unit price differing."
    )
    needs_policy_check: bool = Field(
        description="True when resolving this depends on a contract term rather than "
        "on the operational documents alone."
    )
    policy_question: Optional[str] = Field(
        default=None,
        description="The exact question to put to the contract corpus, if any.",
    )
    recommended_action: Literal[
        "post_as_invoiced", "post_partial", "request_credit_note",
        "query_vendor", "reject", "escalate_to_human",
    ]
    confidence: float = Field(ge=0.0, le=1.0)


class PolicyVerdict(BaseModel):
    """A contractual ruling that can survive an audit."""

    permitted: bool = Field(
        description="Whether the invoiced treatment is permitted by the contract."
    )
    clause_reference: Optional[str] = Field(
        default=None, description="Clause number only, e.g. '7.2'."
    )
    contract_id: Optional[str] = Field(
        default=None, description="Document the clause came from, e.g. 'ACME-MSA-2024'."
    )
    quote: Optional[str] = Field(
        default=None,
        description="Verbatim sentence from the contract, under 40 words. Never paraphrase.",
    )
    limit_applied: Optional[str] = Field(
        default=None, description="The contractual ceiling tested, e.g. '5% escalation cap'."
    )
    observed_value: Optional[str] = Field(
        default=None, description="What the invoice actually showed, e.g. '8.46% uplift'."
    )
    reasoning: str = Field(description="One or two sentences tying the quote to the facts.")
    evidence_found: bool = Field(
        description="False when the corpus returned nothing relevant. Never guess a clause."
    )
    confidence: float = Field(ge=0.0, le=1.0)
