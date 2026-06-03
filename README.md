# Page Pass AI Agent

**Automated Audit System for Asset Credit Verification in Typeset PDF Proofs**

## Overview
In the publishing industry, verifying that asset credits (e.g., permissions and citations for figures, tables, and images) have been accurately inserted into typeset PDF proofs is a recognized operational bottleneck. Editorial staff typically cross-reference a master Excel permissions log with multi-page PDF documents, verifying figure placement, validating credit lines, and ensuring strict formatting compliance. This process is time-intensive and highly susceptible to human error.

**Page Pass AI Agent** automates this verification workflow. It functions as an intelligent orchestration pipeline that dynamically parses the master log, extracts corresponding text regions from the PDF proofs using NLP-driven spatial search, and utilizes a Large Language Model (LLM) to perform semantic and formatting validation.

## Key Features
* **Automated Log Parsing:** Ingests the master Excel permissions log to extract expected assets, credit lines, and contextual descriptions.
* **Intelligent PDF Extraction:** Employs multi-tier text extraction leveraging TF-IDF vectorization to accurately locate the text window surrounding target figures, effectively handling typesetting variations and formatting inconsistencies.
* **LLM-Powered Auditing:** Batches extracted text regions and interfaces with the Gemini AI model to evaluate credits. The LLM performs semantic validation, identifies formatting anomalies (e.g., missing spaces around slashes), and handles minor typographical errors.
* **Data Export & Reporting:** Renders audit results in a reactive web interface with conditional formatting. Provides native functionality to export the finalized audit DataFrame directly to an Excel (`.xlsx`) format for downstream processing.

## Architecture & Technology Stack

The application is built on a decoupled, microservices-oriented architecture:

### 1. Backend Orchestration
* **FastAPI & Uvicorn:** Serves as the primary API gateway, handling asynchronous `multipart/form-data` uploads for simultaneous processing of Excel logs and PDF chapters.
* **Pydantic:** Enforces strict data schemas (`BatchAuditResponse`, `AuditResult`) to guarantee predictable JSON payloads from the LLM.

### 2. Data Processing & Extraction
* **Pandas & Openpyxl:** Processes uploaded `.xlsx` files utilizing regex patterns to isolate actionable items.
* **PyMuPDF (`fitz`):** Extracts raw text from PDF documents with robust error handling for encrypted or malformed files.
* **Scikit-Learn (TF-IDF):** Implements `TfidfVectorizer` and `cosine_similarity` as a fallback heuristic to locate relevant text blocks when direct string matching fails due to typesetting modifications.

### 3. AI Integration
* **Google GenAI SDK:** Interfaces with Gemini models (e.g., `gemini-2.5-pro` or `gemma-4-26b-a4b-it`) asynchronously using `asyncio.gather` for batch processing.
* **Response Sanitization:** Implements robust regex-based sanitization (`re.sub`) to normalize invalid Unicode escapes and guarantee JSON decoder stability against hallucinated markdown or conversational text.

### 4. Frontend Interface
* **Streamlit:** Delivers a fast, stateless web interface.
* **In-Memory File Processing:** Utilizes `io.BytesIO` to generate downloadable Excel reports directly from the active pandas DataFrame without requiring persistent backend storage.

## Workflow Execution

1. **Initialization:** The user uploads the master Excel permissions log and the corresponding PDF chapters via the web interface.
2. **Processing:** The FastAPI backend receives the payload, parses the Excel sheet, and applies the PyMuPDF/Scikit-Learn pipeline to extract targeted text windows for each asset.
3. **Auditing:** The orchestration layer batches the extracted text and queries the LLM. The LLM classifies each asset as `Correct`, `Incorrect`, or `Unfound` based on strict programmatic prompt instructions.
4. **Result Delivery:** The backend returns a structured JSON payload. The frontend visualizes this data in a conditionally-formatted table, providing immediate feedback on compliance status.
5. **Export:** The user can export the verified dataset to an Excel file.

## Getting Started

### 1. Environment Setup
Ensure Python 3.9+ is installed. Initialize a virtual environment and install dependencies:
```bash
python -m venv .myvenv
.\.myvenv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the project root directory and define your Google Gemini API Key:
```env
GEMINI_API_KEY="your_api_key_here"
```

### 3. Initialize Services
Start the FastAPI orchestration server in your terminal:
```bash
.\.myvenv\Scripts\uvicorn main_api:app --port 8000 --reload
```

Open a secondary terminal, activate the environment, and initialize the Streamlit frontend:
```bash
.\.myvenv\Scripts\activate
.\.myvenv\Scripts\streamlit run frontend.py
```
Access the application interface at `http://localhost:8501`.
