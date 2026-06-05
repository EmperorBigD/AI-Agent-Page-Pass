# Page Pass AI Agent

**Automated Audit System for Asset Credit Verification in Typeset PDF Proofs**

## Overview

In the publishing industry, verifying that asset credits (e.g., permissions and citations for figures, tables, and images) have been accurately inserted into typeset PDF proofs is a recognized operational bottleneck. Editorial staff typically cross-reference a master Excel permissions log with multi-page PDF documents, verifying figure placement, validating credit lines, and ensuring strict formatting compliance. This process is time-intensive and highly susceptible to human error.

**Page Pass AI Agent** automates this verification workflow. It functions as an intelligent orchestration pipeline that dynamically parses the master log, extracts corresponding text regions from the PDF proofs using NLP-driven spatial search, and utilizes a Large Language Model (LLM) to perform semantic and formatting validation.

## Key Features

* **Automated Log Parsing:** Ingests the master Excel permissions log with dynamic column resolution and regex-based credit extraction. Raises explicit errors when required columns are missing.
* **Multi-Tier PDF Extraction:** Employs a four-tier strategy to locate asset text in PDFs:
  - **Tier 1** — Direct substring match for the asset spec identifier.
  - **Tier 2** — TF-IDF cosine-similarity search against asset descriptions.
  - **Tier 3** — Spatial image-block fallback for Unnumbered Pictures (UNP).
  - **Tier 4** — Diagnostic tagging with debug information for unfound assets.
* **LLM-Powered Auditing:** Batches extracted text regions and interfaces with the Gemini AI model for semantic validation. Catches formatting anomalies (e.g., missing spaces around slashes), handles bracket-number differences, and tolerates minor typographical errors.
* **Robust Response Sanitization:** Implements regex-based cleanup to normalize invalid Unicode escapes, strip markdown fences, and guarantee JSON decoder stability against hallucinated output.
* **Data Export:** Provides native functionality to export the finalized audit results directly to Excel (`.xlsx`) format for downstream processing.
* **Centralized Configuration:** All tunable parameters (model name, batch size, TF-IDF threshold, text window sizes, API endpoints) are managed through a single configuration module with environment variable overrides.
* **Custom Exception Hierarchy:** Granular error classes (`ExcelParsingError`, `PDFExtractionError`, `LLMResponseError`) enable precise HTTP status code mapping (400, 500, 502) and targeted debugging.
* **Structured Logging:** All modules use a consistent logging format with timestamps and severity levels, replacing ad-hoc print statements.

## Architecture & Technology Stack

The application is built on a decoupled, modular architecture with strict separation of concerns.

### Project Structure

```
├── config.py            # Centralized configuration and environment variables
├── exceptions.py        # Custom exception hierarchy
├── utils.py             # Shared utilities (logger factory, JSON sanitizer)
├── schemas.py           # Pydantic models and TypedDicts for pipeline data
├── excel_handler.py     # Excel permissions log parser
├── pdf_handler.py       # Multi-tier PDF text extraction engine
├── prompts.py           # LLM system prompt and user prompt template
├── ai_agent.py          # Gemini LLM integration and batch processing
├── main_api.py          # FastAPI orchestration backend
├── frontend.py          # Streamlit web interface
├── requirements.txt     # Python dependencies
└── .env                 # API key configuration (not committed)
```

### Backend Orchestration

* **FastAPI & Uvicorn:** Serves as the primary API gateway, handling asynchronous `multipart/form-data` uploads for simultaneous processing of Excel logs and PDF chapters. Includes a `/health` endpoint for liveness probes.
* **Pydantic:** Enforces strict data schemas (`AssetSpec`, `AuditResult`, `BatchAuditResponse`) across the entire pipeline, from Excel extraction through to LLM response validation.
* **Custom Exceptions:** `ExcelParsingError`, `PDFExtractionError`, and `LLMResponseError` are caught at the API layer and mapped to appropriate HTTP status codes (400 for client errors, 502 for upstream LLM failures).

### Data Processing & Extraction

* **Pandas & Openpyxl:** Processes uploaded `.xlsx` files with dynamic column resolution and regex-based credit line extraction.
* **PyMuPDF (`fitz`):** Extracts raw text from PDF documents with robust error handling for encrypted, corrupted, or empty files.
* **Scikit-Learn (TF-IDF):** Implements `TfidfVectorizer` and cosine similarity as a fallback heuristic to locate relevant text blocks when direct string matching fails due to typesetting modifications.

### AI Integration

* **Google GenAI SDK:** Interfaces with Gemini models asynchronously using `asyncio.gather` for concurrent batch processing.
* **Response Sanitization:** A dedicated `sanitize_llm_json()` utility handles markdown fence stripping, JSON brace extraction, and invalid backslash escape normalization.

### Frontend Interface

* **Streamlit:** Delivers a reactive web interface with a dark theme, gradient-styled controls, and conditional row formatting (green/red/yellow) based on audit status.
* **In-Memory File Processing:** Utilizes `io.BytesIO` to generate downloadable Excel reports directly from the active DataFrame without requiring persistent storage.

## Workflow Execution

1. **Initialization:** The user uploads the master Excel permissions log and the corresponding PDF chapters via the web interface.
2. **Processing:** The FastAPI backend receives the payload, parses the Excel sheet with column validation, and applies the multi-tier PDF extraction pipeline for each asset.
3. **Auditing:** The orchestration layer batches the extracted text and queries the LLM. Each asset is classified as `Correct`, `Incorrect`, or `Unfound` based on strict programmatic prompt instructions.
4. **Result Delivery:** The backend returns a structured JSON payload. The frontend visualizes results in a conditionally-formatted table with immediate compliance feedback.
5. **Export:** The user can download the complete audit dataset as an Excel file.

## Getting Started

### 1. Environment Setup

Ensure Python 3.10+ is installed. Initialize a virtual environment and install dependencies:

```bash
python -m venv .myvenv
.\.myvenv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root directory:

```env
GEMINI_API_KEY="your_api_key_here"
```

Optional environment variables for advanced configuration:

| Variable | Default | Description |
|---|---|---|
| `GEMINI_MODEL` | `gemma-4-31b-it` | LLM model identifier |
| `BATCH_SIZE` | `20` | Assets per LLM batch request |
| `TFIDF_THRESHOLD` | `0.05` | Minimum cosine similarity for Tier 2 matches |
| `API_HOST` | `http://localhost:8000` | Backend API base URL |
| `API_TIMEOUT` | `300` | Frontend request timeout (seconds) |

### 3. Initialize Services

Start the FastAPI orchestration server:

```bash
.\.myvenv\Scripts\uvicorn main_api:app --port 8000 --reload
```

Open a secondary terminal, activate the environment, and initialize the Streamlit frontend:

```bash
.\.myvenv\Scripts\activate
.\.myvenv\Scripts\streamlit run frontend.py
```

Access the application interface at `http://localhost:8501`.

### 4. Health Check

Verify the backend is running:

```bash
curl http://localhost:8000/health
```

## Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | API framework |
| `uvicorn` | ASGI server |
| `python-multipart` | File upload handling |
| `python-dotenv` | Environment variable management |
| `pandas` | DataFrame operations |
| `openpyxl` | Excel file I/O |
| `PyMuPDF` | PDF text extraction |
| `scikit-learn` | TF-IDF vectorization and cosine similarity |
| `google-genai` | Gemini LLM API client |
| `pydantic` | Data validation and schema enforcement |
| `requests` | HTTP client for frontend → backend communication |
| `streamlit` | Web interface framework |
| `numpy` | Numerical operations |
