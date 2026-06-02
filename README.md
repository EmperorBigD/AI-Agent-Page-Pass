# 📄 Page Pass AI Agent

**Automated Audit System to verify asset credits in typeset PDF proofs against an Excel permissions log.**

## 💡 The Problem
In the publishing industry, verifying that asset credits (like permissions and citations for figures, tables, and images) have been accurately inserted into typeset PDF proofs is a massive bottleneck. Editors must manually cross-reference a master Excel permissions log with a multi-page PDF document, searching for the figure, checking the credit line, and ensuring there are no typos or missing slashes. It is tedious, error-prone, and time-consuming.

## 🚀 The Solution
**Page Pass AI Agent** completely automates this workflow. It acts as an intelligent orchestration pipeline that:
1. **Parses the Master Log:** Reads the Excel file to extract the expected assets, expected credit lines, and descriptions.
2. **Scans the PDF Proofs:** Uses advanced multi-tier text extraction (leveraging TF-IDF vectorization) to locate the exact text window surrounding the target figure in the PDF, even if there are formatting inconsistencies (e.g., "Figure 06.07" vs "Fig. 6.7").
3. **AI Auditing:** Batches the extracted text windows and sends them to the Gemini AI model to semantically evaluate the credits. It catches missing spaces around slashes, ignores arbitrary bracketed numbers, and handles minor typos gracefully.
4. **Beautiful Presentation:** Returns the audit results in a sleek, dark-themed Streamlit UI, using conditional formatting to highlight exactly what passed and what failed.

---

## 🛠️ The Tech Stack (The Fun Part!)

We built this using a robust, decoupled architecture:

### 1. Backend Orchestration
*   **FastAPI & Uvicorn:** Serves as the central nervous system, handling asynchronous `multipart/form-data` uploads for both the Excel log and the PDF chapters simultaneously.
*   **Pydantic:** Enforces strict data schemas (`BatchAuditResponse`, `AuditResult`) to guarantee predictable JSON payloads from the AI.

### 2. Data Processing & Extraction
*   **Pandas & Openpyxl:** Reads and filters the uploaded `.xlsx` files using strict Regex patterns to grab only actionable items.
*   **PyMuPDF (`fitz`):** Extracts raw text from the PDFs.
*   **Scikit-Learn (TF-IDF):** Our secret weapon for PDF extraction! When simple string matching fails due to typesetting variations, we use `TfidfVectorizer` and `cosine_similarity` to find the most relevant block of text surrounding the target figure.

### 3. AI Intelligence
*   **Google GenAI SDK (`google-genai`):** Communicates with the Gemini models (e.g., `gemini-2.5-pro` or `gemma-4-26b-a4b-it`) asynchronously using `asyncio.gather` to process batches of 20 assets at a time.
*   **Robust JSON Parsing:** We implemented Regex fallbacks (`re.search`) to slice out valid JSON blocks from the AI's response, completely immunizing the system against Markdown ticks or rogue conversational text (`Extra data` JSONDecodeErrors).

### 4. Frontend UI
*   **Streamlit:** Provides a fast, stateless, and interactive UI.
*   **Custom CSS:** Injected premium CSS to enforce a sleek dark mode (`#0e1117`), gradient buttons with hover micro-animations, and modern typography (`Inter`).
*   **Session State:** Dynamically hides the upload forms once the audit is running, seamlessly transitioning into the final conditionally-formatted Pandas DataFrame.

---

## 🚦 Walkthrough: How It Works

1. **Upload:** You drop your Excel permissions log and your PDF chapters into the centered dropzone on the web UI.
2. **Process:** You click **Run Audit**. The UI hides the uploader and spins up a loading indicator.
3. **Extract:** The FastAPI backend receives the files, parses the Excel sheet, and uses PyMuPDF + Scikit-Learn to hunt down the exact text windows in the PDF for every single asset.
4. **Audit:** The AI Agent groups these text windows into batches and queries the LLM. The LLM grades them as `Correct`, `Incorrect`, or `Unfound` based on a strict set of prompt instructions (e.g., strict slash spacing).
5. **Results:** The backend returns a structured JSON payload to Streamlit, which renders a beautiful table.
   *   🟢 **Green:** The credit is perfect.
   *   🔴 **Red:** The credit is incorrect, altered, or missing.
   *   🟡 **Yellow:** The figure couldn't be found in the PDF.

---

## 💻 Getting Started

### 1. Clone & Setup Environment
Ensure you have Python installed. Create a virtual environment and install dependencies:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set API Key
Create a `.env` file in the root directory and add your Google Gemini API Key:
```env
GEMINI_API_KEY="your_api_key_here"
```

### 3. Run the Backend
Start the FastAPI orchestration server in your terminal:
```bash
venv\Scripts\uvicorn main_api:app --port 8000 --reload
```

### 4. Run the Frontend
Open a *new* terminal, activate the environment, and start Streamlit:
```bash
venv\Scripts\activate
streamlit run frontend.py
```
*Navigate to `http://localhost:8501` to use the Agent!*
