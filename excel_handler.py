"""
Excel permissions log handler for the Page Pass AI Agent.

Reads an uploaded ``.xlsx`` file, applies business-rule filters,
and extracts the expected credit lines using regex patterns.
"""

from __future__ import annotations

import re
from typing import Optional

import pandas as pd

from exceptions import ExcelParsingError
from schemas import AssetSpec
from utils import setup_logger

logger = setup_logger(__name__)

# Regex patterns for extracting expected credits from the instruction column
_PATTERN_REPLACE = re.compile(r"REPLACE\s+\(?[^\)]*\)?\s+WITH\s+(.+)", re.IGNORECASE)
_PATTERN_ADD = re.compile(r"ADD THE FOLLOWING CREDIT:\s+(.+)", re.IGNORECASE)

# Instructions that indicate no on-page credit is needed
_DROP_INSTRUCTIONS: list[str] = [
    "no on page credit is required",
    "no on-page credit is required",
    "no change to ms",
]


# ──────────────────────────────────────────────
# Private Helpers
# ──────────────────────────────────────────────


def _resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    """Map logical column names to their actual names in the DataFrame.

    Uses case-insensitive matching and common fallback heuristics.

    Args:
        df: The raw DataFrame read from the Excel file.

    Returns:
        A dictionary with keys ``spec_status``, ``perm_status``,
        ``credit_instr``, ``spec``, and ``description`` mapped to the
        actual column names found in *df*.

    Raises:
        ExcelParsingError: If any of the three required columns
            (Spec Status, Permissions Status, Credit Processing Instruction)
            cannot be located.
    """
    col_map = {col.lower(): col for col in df.columns}

    spec_status = col_map.get("spec status")
    perm_status = col_map.get("permissions status")
    credit_instr = col_map.get("credit processing instruction")

    missing: list[str] = []
    if not spec_status:
        missing.append("Spec Status")
    if not perm_status:
        missing.append("Permissions Status")
    if not credit_instr:
        missing.append("Credit Processing Instruction")

    if missing:
        raise ExcelParsingError(
            f"Required column(s) not found in the Excel file: {', '.join(missing)}. "
            f"Available columns: {list(df.columns)}"
        )

    # Spec column (the figure/asset identifier)
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

    # Description column
    desc_col = next(
        (col for col in df.columns if "description" in col.lower()), None
    )
    if not desc_col:
        desc_col = next(
            (col for col in df.columns if "detail" in col.lower()),
            df.columns[1] if len(df.columns) > 1 else df.columns[0],
        )

    return {
        "spec_status": spec_status,
        "perm_status": perm_status,
        "credit_instr": credit_instr,
        "spec": spec_col,
        "description": desc_col,
    }


def _extract_expected_credit(instruction: str) -> Optional[str]:
    """Try to extract the expected credit line from a credit processing instruction.

    Applies two regex patterns in order:
    1. ``REPLACE ... WITH <credit>``
    2. ``ADD THE FOLLOWING CREDIT: <credit>``

    Args:
        instruction: The raw cell value from the Credit Processing Instruction column.

    Returns:
        The extracted credit string, or ``None`` if no pattern matched.
    """
    match = _PATTERN_REPLACE.search(instruction)
    if match:
        return match.group(1).strip()

    match = _PATTERN_ADD.search(instruction)
    if match:
        return match.group(1).strip()

    return None


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def process_excel(filepath: str) -> list[AssetSpec]:
    """Parse the Excel permissions log and return actionable asset specs.

    Applies the following pipeline:

    1. **Column resolution** — locates required columns case-insensitively.
    2. **Row filtering** — keeps rows where Spec Status is *Approved* and
       Permissions Status is *Granted*.
    3. **Instruction exclusion** — drops rows whose credit instruction
       matches a known "no credit needed" phrase.
    4. **Credit extraction** — uses regex to pull the expected credit text
       from the instruction column.

    Args:
        filepath: Absolute path to the uploaded ``.xlsx`` file.

    Returns:
        A list of :class:`AssetSpec` objects ready for the PDF extraction
        pipeline.

    Raises:
        ExcelParsingError: If required columns are missing.
    """
    logger.info("Reading Excel file: %s", filepath)
    df = pd.read_excel(filepath)

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()
    logger.debug("Detected columns: %s", list(df.columns))

    # Resolve logical → actual column mapping
    cols = _resolve_columns(df)

    # Filter 1: Approved + Granted
    df = df[
        (df[cols["spec_status"]].astype(str).str.strip().str.lower() == "approved")
        & (df[cols["perm_status"]].astype(str).str.strip().str.lower() == "granted")
    ]
    logger.info("Rows after Approved/Granted filter: %d", len(df))

    # Filter 2: Exclude "no credit needed" instructions
    df = df[
        ~df[cols["credit_instr"]]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(_DROP_INSTRUCTIONS)
    ]
    logger.info("Rows after exclusion filter: %d", len(df))

    # Extract credits
    results: list[AssetSpec] = []

    for _, row in df.iterrows():
        instruction = str(row.get(cols["credit_instr"], "")).strip()
        expected_credit = _extract_expected_credit(instruction)

        if expected_credit:
            asset = AssetSpec(
                spec=str(row.get(cols["spec"], "")).strip(),
                expected_credit=expected_credit,
                description=str(row.get(cols["description"], "")).strip(),
            )
            results.append(asset)

    logger.info("Extracted %d actionable assets from Excel", len(results))
    return results


# ──────────────────────────────────────────────
# Standalone Test
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python excel_handler.py <path_to_excel_file>")
        sys.exit(1)

    assets = process_excel(sys.argv[1])
    for a in assets:
        print(f"  {a.spec:20s} | {a.expected_credit[:60]}")
    print(f"\nTotal: {len(assets)} assets")
