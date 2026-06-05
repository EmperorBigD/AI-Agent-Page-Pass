"""
Data schemas for the Page Pass AI Agent.

Defines Pydantic models for strict validation of data flowing through
the Excel → PDF → LLM pipeline, and TypedDicts for internal structures.
"""

from __future__ import annotations

from typing import Optional, TypedDict, Any

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Internal Pipeline Types
# ──────────────────────────────────────────────

class AssetSpec(BaseModel):
    """A single asset extracted from the Excel permissions log.

    This model represents the *input* to the PDF extraction and LLM
    audit stages.
    """

    spec: str = Field(..., description="The asset specification, e.g. 'Figure 4.1'")
    expected_credit: str = Field(
        ..., description="The credit line that should appear in the PDF"
    )
    description: str = Field(
        "", description="Description of the asset used for TF-IDF fallback matching"
    )


class PageData(TypedDict):
    """Typed representation of a single loaded PDF page."""

    pdf: str
    page_num: int
    page: Any  # fitz.Page — not typed to avoid hard PyMuPDF dependency on import
    text: str


# ──────────────────────────────────────────────
# LLM Response Types
# ──────────────────────────────────────────────


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
