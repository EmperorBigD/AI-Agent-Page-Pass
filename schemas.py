from pydantic import BaseModel, Field
from typing import Optional


class AuditResult(BaseModel):
    spec: str = Field(..., description="The asset specification, e.g., 'Figure 4.1'")
    expected_credit: str = Field(
        ..., description="The expected credit line to be found in the PDF"
    )
    description: str = Field(
        ..., description="Description of the asset used for TF-IDF matching"
    )
    extracted_pdf_text: Optional[str] = Field(
        None, description="The text window extracted from the PDF"
    )
    status: str = Field(
        ...,
        description="The audit status: 'Correct', 'Incorrect', 'Unfound', or a detailed fallback status",
    )
    reasoning: Optional[str] = Field(
        None,
        description="The LLM's reasoning for why it marked the status as Correct or Incorrect",
    )


class BatchAuditResponse(BaseModel):
    results: list[AuditResult]
