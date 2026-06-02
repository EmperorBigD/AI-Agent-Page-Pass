import os
import shutil
import tempfile
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from excel_handler import process_excel
from pdf_handler import extract_pdf_windows
from ai_agent import run_audit_batch

app = FastAPI(title="Page Pass AI Agent API", version="1.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/audit")
async def audit_assets(
    excel_file: UploadFile = File(...), pdf_files: List[UploadFile] = File(...)
):
    if not excel_file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Invalid excel file format")

    temp_dir = tempfile.mkdtemp()

    try:
        # Save Excel File
        excel_path = os.path.join(temp_dir, excel_file.filename)
        with open(excel_path, "wb") as buffer:
            shutil.copyfileobj(excel_file.file, buffer)

        # Save PDF Files
        saved_pdf_paths = []
        for pdf in pdf_files:
            if not pdf.filename.endswith(".pdf"):
                raise HTTPException(
                    status_code=400, detail=f"Invalid PDF file: {pdf.filename}"
                )
            pdf_path = os.path.join(temp_dir, pdf.filename)
            with open(pdf_path, "wb") as buffer:
                shutil.copyfileobj(pdf.file, buffer)
            saved_pdf_paths.append(pdf_path)

        # Phase 1: Excel Pipeline
        assets = process_excel(excel_path)
        if not assets:
            return {
                "results": [],
                "message": "No actionable assets found in the Excel file.",
            }

        # Phase 2: PDF Pipeline
        extracted_assets = extract_pdf_windows(saved_pdf_paths, assets)

        # Phase 3: AI Audit
        final_results = await run_audit_batch(extracted_assets)

        return {"results": final_results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
