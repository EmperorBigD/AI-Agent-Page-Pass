import pandas as pd
import re


def process_excel(filepath: str) -> list[dict]:
    # Read the excel file
    df = pd.read_excel(filepath)

    # Strip whitespace from column names to ensure safe access
    df.columns = df.columns.str.strip()

    # Find necessary columns (case-insensitive match)
    col_map = {col.lower(): col for col in df.columns}

    spec_status_col = col_map.get("spec status")
    perm_status_col = col_map.get("permissions status")
    credit_instr_col = col_map.get("credit processing instruction")

    if not (spec_status_col and perm_status_col and credit_instr_col):
        # Fallback if exact columns aren't found, try to guess or just return empty
        # Real-world we might want to raise an error
        pass

    # Filter 1: Keep rows where Spec Status == "Approved" AND Permissions Status == "Granted"
    if spec_status_col and perm_status_col:
        df = df[
            (df[spec_status_col].astype(str).str.strip().str.lower() == "approved")
            & (df[perm_status_col].astype(str).str.strip().str.lower() == "granted")
        ]

    # Filter 2: Drop rows where Credit Processing Instruction exactly matches exclusions
    drop_instructions = [
        "no on page credit is required",
        "no on-page credit is required",
        "no change to ms",
    ]
    if credit_instr_col:
        df = df[
            ~df[credit_instr_col]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(drop_instructions)
        ]

    # Regex Extraction
    pattern1 = re.compile(r"REPLACE\s+\(?[^\)]*\)?\s+WITH\s+(.+)", re.IGNORECASE)
    pattern2 = re.compile(r"ADD THE FOLLOWING CREDIT:\s+(.+)", re.IGNORECASE)

    results = []

    # Identify Spec and Description columns dynamically
    spec_col = next((col for col in df.columns if "spec" in col.lower()), None)
    if not spec_col:
        spec_col = next(
            (
                col
                for col in df.columns
                if "figure" in col.lower() or "asset" in col.lower()
            ),
            df.columns[0],
        )

    desc_col = next((col for col in df.columns if "description" in col.lower()), None)
    if not desc_col:
        desc_col = next(
            (col for col in df.columns if "detail" in col.lower()),
            df.columns[1] if len(df.columns) > 1 else df.columns[0],
        )

    for _, row in df.iterrows():
        if credit_instr_col:
            instruction = str(row.get(credit_instr_col, "")).strip()
        else:
            instruction = ""

        match1 = pattern1.search(instruction)
        match2 = pattern2.search(instruction)

        expected_credit = None
        if match1:
            expected_credit = match1.group(1).strip()
        elif match2:
            expected_credit = match2.group(1).strip()

        if expected_credit:
            results.append(
                {
                    "spec": str(row.get(spec_col, "")).strip(),
                    "expected_credit": expected_credit,
                    "description": str(row.get(desc_col, "")).strip(),
                }
            )

    return results
