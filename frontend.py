"""Streamlit frontend for the Page Pass AI Agent."""

import streamlit as st
import requests
import pandas as pd
import io

from config import API_AUDIT_ENDPOINT, API_REQUEST_TIMEOUT

st.set_page_config(page_title="Page Pass AI", layout="wide", page_icon="📄")

# Inject Premium Custom CSS (Dark Theme)
st.markdown(
    """
    <style>
    /* Main Background & Fonts */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Styling */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {
        color: #fafafa;
    }
    h1 {
        font-weight: 700;
        letter-spacing: -1px;
    }
    
    /* Button Styling */
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
        color: white;
    }
    
    /* Dataframe Container */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.3), 0 1px 2px 0 rgba(0, 0, 0, 0.2);
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("📄 Page Pass AI")
st.markdown(
    "**Automated Audit System** | Verify asset credits in typeset PDF proofs against your permissions log."
)


def color_rows(row):
    status = str(row.get("status", "")).lower()
    if "correct" in status and "incorrect" not in status:
        return ["background-color: #0d3d20; color: #75f0a0"] * len(row)  # Dark Green
    elif "incorrect" in status:
        return ["background-color: #4a151b; color: #ff8c9b"] * len(row)  # Dark Red
    elif "unfound" in status:
        return ["background-color: #4d3a00; color: #ffda6a"] * len(row)  # Dark Yellow
    elif "error" in status:
        return ["background-color: #4a151b; color: #ff8c9b"] * len(row)  # Dark Red
    return [""] * len(row)


# Initialize session state for storing results
if "audit_results" not in st.session_state:
    st.session_state.audit_results = None

if st.session_state.audit_results is None:
    # --- UPLOAD SECTION (CENTERED) ---
    st.write("### Upload Files")
    excel_file = st.file_uploader("Upload Excel Permissions Log", type=["xlsx", "xls"])
    pdf_files = st.file_uploader(
        "Upload PDF Proofs (Chapter-wise)", type=["pdf"], accept_multiple_files=True
    )

    submit_btn = st.button("Run Audit", type="primary")

    if submit_btn:
        if not excel_file:
            st.error("Please upload the Excel Permissions Log.")
        elif not pdf_files:
            st.error("Please upload at least one PDF proof.")
        else:
            with st.spinner(
                "Processing files and running AI audit. This may take a moment..."
            ):
                try:
                    # Prepare files
                    files = []
                    files.append(
                        (
                            "excel_file",
                            (
                                excel_file.name,
                                excel_file.getvalue(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ),
                        )
                    )
                    for pdf in pdf_files:
                        files.append(
                            ("pdf_files", (pdf.name, pdf.getvalue(), "application/pdf"))
                        )

                    # Make API Request
                    response = requests.post(
                        API_AUDIT_ENDPOINT, files=files, timeout=API_REQUEST_TIMEOUT
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.audit_results = data.get("results", [])
                        st.rerun()  # Rerun to hide the upload form
                    else:
                        st.error(f"API Error: {response.status_code}")
                        st.json(response.json())

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

else:
    # --- RESULTS SECTION ---
    results = st.session_state.audit_results

    if results:
        st.success(f"Audit Complete! Processed {len(results)} assets.")

        df = pd.DataFrame(results)

        # Reorder columns for better UX if they exist
        cols = [
            "status",
            "spec",
            "description",
            "expected_credit",
            "extracted_pdf_text",
            "reasoning",
        ]
        existing_cols = [c for c in cols if c in df.columns]
        # Add any extra columns
        existing_cols.extend([c for c in df.columns if c not in existing_cols])
        df = df[existing_cols]

        # Apply conditional formatting
        styled_df = df.style.apply(color_rows, axis=1)

        st.dataframe(styled_df, width="stretch", height=600)

        # --- EXCEL DOWNLOAD FEATURE ---
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Audit Results")

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="⬇️ Download Results as Excel",
                data=buffer.getvalue(),
                file_name="audit_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
        with col2:
            if st.button("🔄 Run Another Audit", width="stretch"):
                st.session_state.audit_results = None
                st.rerun()
    else:
        st.warning("No results returned.")
        if st.button("Run Another Audit"):
            st.session_state.audit_results = None
            st.rerun()
