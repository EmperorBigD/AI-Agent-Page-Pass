"""
FastAPI backend for the Page Pass AI Agent.

Serves as the orchestration layer that receives file uploads from the
Streamlit frontend, pipes them through the Excel → PDF → LLM pipeline,
and returns structured audit results.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from excel_handler import process_excel
from pdf_handler import extract_pdf_windows
from ai_agent import run_audit_batch
from exceptions import ExcelParsingError, PDFExtractionError, LLMResponseError
from utils import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="Page Pass AI Agent API", version="2.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────


@app.get("/health")
async def health_check():
    """Quick liveness probe."""
    return {"status": "ok"}


# ──────────────────────────────────────────────
# Audit Endpoint
# ──────────────────────────────────────────────


@app.post("/api/v1/audit")
async def audit_assets(
    excel_file: UploadFile = File(...),
    pdf_files: List[UploadFile] = File(...),
):
    """Run the full Excel → PDF → LLM audit pipeline.

    Accepts a single Excel permissions log and one or more PDF chapter
    proofs as multipart file uploads.

    Returns:
        A JSON object with a ``results`` key containing the list of
        audit result dictionaries.
    """
    if not excel_file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Invalid excel file format")

    temp_dir = tempfile.mkdtemp()
    logger.info("Created temp directory: %s", temp_dir)

    try:
        # ── Save Excel File ──
        excel_path = os.path.join(temp_dir, excel_file.filename)
        with open(excel_path, "wb") as buffer:
            shutil.copyfileobj(excel_file.file, buffer)
        logger.info("Saved Excel: %s", excel_file.filename)

        # ── Save PDF Files ──
        saved_pdf_paths: list[str] = []
        for pdf in pdf_files:
            if not pdf.filename.endswith(".pdf"):
                raise HTTPException(
                    status_code=400, detail=f"Invalid PDF file: {pdf.filename}"
                )
            pdf_path = os.path.join(temp_dir, pdf.filename)
            with open(pdf_path, "wb") as buffer:
                shutil.copyfileobj(pdf.file, buffer)
            saved_pdf_paths.append(pdf_path)
        logger.info("Saved %d PDF(s)", len(saved_pdf_paths))

        # ── Phase 1: Excel Pipeline ──
        try:
            assets = process_excel(excel_path)
        except ExcelParsingError as e:
            logger.error("Excel parsing failed: %s", e)
            raise HTTPException(status_code=400, detail=str(e))

        if not assets:
            return {
                "results": [],
                "message": "No actionable assets found in the Excel file.",
            }

        # Convert AssetSpec models to dicts for the downstream pipeline
        asset_dicts = [a.model_dump() for a in assets]

        # ── Phase 2: PDF Pipeline ──
        try:
            extracted_assets = extract_pdf_windows(saved_pdf_paths, asset_dicts)
        except PDFExtractionError as e:
            logger.error("PDF extraction failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

        # ── Phase 3: AI Audit ──
        try:
            final_results = await run_audit_batch(extracted_assets)
        except LLMResponseError as e:
            logger.error("LLM audit failed: %s", e)
            raise HTTPException(status_code=502, detail=str(e))

        logger.info("Audit complete: %d results", len(final_results))
        return {"results": final_results}

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is

    except Exception as e:
        logger.exception("Unexpected error during audit")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.debug("Cleaned up temp directory: %s", temp_dir)


# ──────────────────────────────────────────────
# Standalone Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
