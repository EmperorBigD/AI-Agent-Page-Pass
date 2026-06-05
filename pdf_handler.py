"""
PDF text extraction handler for the Page Pass AI Agent.

Loads chapter PDFs via PyMuPDF, builds a TF-IDF index of their pages,
and applies a four-tier strategy to locate the text window surrounding
each asset's figure/table reference.

Tiers:
    1. **Exact Match** — direct substring search for the spec string.
    2. **TF-IDF Lexical Match** — cosine similarity between the asset
       description and every page.
    3. **Spatial UNP Search** — image-block based fallback for
       unnumbered pictures.
    4. **Unfound** — tags the asset with diagnostic debug information.
"""

from __future__ import annotations

import fitz  # PyMuPDF
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import spmatrix

from config import (
    TFIDF_THRESHOLD,
    PDF_WINDOW_BEFORE,
    PDF_WINDOW_AFTER,
    TFIDF_WINDOW_SIZE,
)
from schemas import PageData
from utils import setup_logger

logger = setup_logger(__name__)


# ──────────────────────────────────────────────
# PDF Loading
# ──────────────────────────────────────────────


def load_pdf_pages(pdf_paths: list[str]) -> tuple[list[PageData], list[str]]:
    """Open each PDF and extract page-level text.

    Args:
        pdf_paths: Absolute paths to the uploaded PDF files.

    Returns:
        A tuple of ``(pages, errors)`` where *pages* is a list of
        :class:`PageData` dicts and *errors* collects any loading failures.
    """
    all_pages: list[PageData] = []
    pdf_errors: list[str] = []

    for path in pdf_paths:
        try:
            doc = fitz.open(path)
            if doc.is_encrypted:
                pdf_errors.append(f"PDF is encrypted/password protected: {path}")
                logger.warning("Skipping encrypted PDF: %s", path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                all_pages.append(
                    PageData(pdf=path, page_num=page_num, page=page, text=text)
                )
        except Exception as e:
            error_msg = f"Error loading {path}: {e}"
            logger.error(error_msg)
            pdf_errors.append(str(e))

    logger.info("Loaded %d pages from %d PDF(s)", len(all_pages), len(pdf_paths))
    return all_pages, pdf_errors


# ──────────────────────────────────────────────
# TF-IDF Index
# ──────────────────────────────────────────────


def build_tfidf_index(
    pages: list[PageData],
) -> tuple[TfidfVectorizer, spmatrix | None]:
    """Fit a TF-IDF vectorizer on the text of all loaded pages.

    Args:
        pages: The list of loaded PDF pages.

    Returns:
        A tuple of ``(vectorizer, tfidf_matrix)``.  If pages are empty or
        the vocabulary is empty, *tfidf_matrix* will be ``None``.
    """
    vectorizer = TfidfVectorizer(stop_words="english")
    page_texts = [p["text"] for p in pages]

    if not page_texts:
        return vectorizer, None

    try:
        tfidf_matrix = vectorizer.fit_transform(page_texts)
        return vectorizer, tfidf_matrix
    except ValueError:
        logger.warning("TF-IDF vocabulary was empty — no usable text in PDFs")
        return vectorizer, None


# ──────────────────────────────────────────────
# Tier Functions
# ──────────────────────────────────────────────


def _tier1_exact_match(asset: dict, pages: list[PageData]) -> bool:
    """Tier 1: Direct substring search for the spec string.

    Searches every page for an exact occurrence of ``asset["spec"]``
    and, if found, extracts a surrounding text window.

    Args:
        asset: The asset dictionary (mutated in-place on success).
        pages: All loaded PDF pages.

    Returns:
        ``True`` if the spec was found, ``False`` otherwise.
    """
    spec: str = asset.get("spec", "")
    for p in pages:
        text = p["text"]
        idx = text.find(spec)
        if idx != -1:
            start = max(0, idx - PDF_WINDOW_BEFORE)
            end = min(len(text), idx + len(spec) + PDF_WINDOW_AFTER)
            asset["extracted_pdf_text"] = text[start:end]
            asset["status"] = "Found (Tier 1)"
            logger.debug("Tier 1 hit for '%s' on page %d", spec, p["page_num"])
            return True
    return False


def _tier2_tfidf_match(
    asset: dict,
    pages: list[PageData],
    vectorizer: TfidfVectorizer,
    tfidf_matrix: spmatrix,
) -> tuple[bool, float, int]:
    """Tier 2: TF-IDF cosine-similarity search.

    Transforms the asset description into the fitted TF-IDF space and
    finds the page with the highest cosine similarity.

    Args:
        asset: The asset dictionary (mutated in-place on success).
        pages: All loaded PDF pages.
        vectorizer: The fitted TF-IDF vectorizer.
        tfidf_matrix: The fitted TF-IDF matrix for all pages.

    Returns:
        A tuple of ``(found, best_score, best_idx)`` so callers can
        use the score for debug output even on failure.
    """
    description: str = asset.get("description", "")
    if not description:
        return False, 0.0, -1

    try:
        desc_vector = vectorizer.transform([description])
        cosine_similarities = (tfidf_matrix * desc_vector.T).toarray().flatten()

        best_idx = int(np.argmax(cosine_similarities))
        best_score = float(cosine_similarities[best_idx])

        if best_score > TFIDF_THRESHOLD:
            text = pages[best_idx]["text"]
            asset["extracted_pdf_text"] = text[:TFIDF_WINDOW_SIZE]
            asset["status"] = f"Found (Tier 2) - Score: {best_score:.2f}"
            logger.debug(
                "Tier 2 hit for '%s' — score %.4f on page %d",
                asset.get("spec"),
                best_score,
                pages[best_idx]["page_num"],
            )
            return True, best_score, best_idx

        return False, best_score, best_idx

    except Exception as e:
        logger.error("Tier 2 error for spec '%s': %s", asset.get("spec"), e)
        return False, 0.0, -1


def _tier3_spatial_unp(asset: dict, pages: list[PageData]) -> bool:
    """Tier 3: Image-block spatial search for Unnumbered Pictures.

    Falls back to scanning pages for physical image blocks when the
    spec contains "UNP" or all prior tiers failed.

    Args:
        asset: The asset dictionary (mutated in-place on success).
        pages: All loaded PDF pages.

    Returns:
        ``True`` if an image-bearing page was found, ``False`` otherwise.
    """
    spec: str = asset.get("spec", "")
    if "unp" not in spec.lower():
        return False

    for p in pages:
        page = p["page"]
        images = page.get_images(full=True)
        if images:
            text = p["text"]
            asset["extracted_pdf_text"] = (
                text[:500] + "\n[Extracted via Tier 3 Fallback]"
            )
            asset["status"] = "Found (Tier 3)"
            logger.debug("Tier 3 hit for '%s' on page %d", spec, p["page_num"])
            return True

    return False


def _build_unfound_debug(
    asset: dict,
    pages: list[PageData],
    pdf_errors: list[str],
    best_score: float,
    best_idx: int,
) -> None:
    """Populate an unfound asset with diagnostic debug information.

    Args:
        asset: The asset dictionary (mutated in-place).
        pages: All loaded PDF pages.
        pdf_errors: Errors collected during PDF loading.
        best_score: The best TF-IDF similarity score encountered.
        best_idx: The page index corresponding to *best_score*.
    """
    asset["status"] = "Unfound"
    description = asset.get("description", "")

    if len(pages) == 0:
        error_str = (
            " | ".join(pdf_errors) if pdf_errors else "Unknown reason (0 byte file?)"
        )
        asset["extracted_pdf_text"] = (
            f"DEBUG: PyMuPDF failed to load any pages. Errors: {error_str}"
        )
    elif not any(p["text"].strip() for p in pages):
        asset["extracted_pdf_text"] = (
            "DEBUG: PyMuPDF could not read ANY text from the PDF. "
            "It might be a scanned image with no embedded text layer."
        )
    elif not description:
        asset["extracted_pdf_text"] = (
            "DEBUG: Skipped Tier 2 because 'description' from Excel was empty."
        )
    else:
        asset["extracted_pdf_text"] = (
            f"DEBUG: Found text, but the highest similarity score for this "
            f"description was only {best_score:.4f} (needs > {TFIDF_THRESHOLD}). "
            f"The closest match was on page index {best_idx}. Either the PDF "
            f"doesn't contain this asset, or the text differs drastically."
        )

    logger.info(
        "Unfound: '%s' — %s", asset.get("spec"), asset["extracted_pdf_text"][:120]
    )


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def extract_pdf_windows(pdf_paths: list[str], assets: list[dict]) -> list[dict]:
    """Orchestrate the multi-tier PDF text extraction pipeline.

    For each asset, tries Tier 1 → 2 → 3 in order.  If all tiers fail,
    tags the asset as *Unfound* with debug diagnostics.

    Args:
        pdf_paths: Absolute paths to the uploaded PDF chapter files.
        assets: A list of asset dictionaries (each containing at minimum
            ``spec``, ``expected_credit``, and ``description``).

    Returns:
        The same list of asset dictionaries, now enriched with
        ``extracted_pdf_text`` and ``status`` fields.
    """
    pages, pdf_errors = load_pdf_pages(pdf_paths)
    vectorizer, tfidf_matrix = build_tfidf_index(pages)

    results: list[dict] = []

    for asset in assets:
        # Tier 1
        if _tier1_exact_match(asset, pages):
            results.append(asset)
            continue

        # Tier 2
        best_score = 0.0
        best_idx = -1
        if tfidf_matrix is not None:
            found, best_score, best_idx = _tier2_tfidf_match(
                asset, pages, vectorizer, tfidf_matrix
            )
            if found:
                results.append(asset)
                continue

        # Tier 3
        if _tier3_spatial_unp(asset, pages):
            results.append(asset)
            continue

        # Tier 4 (Unfound)
        _build_unfound_debug(asset, pages, pdf_errors, best_score, best_idx)
        results.append(asset)

    return results


# ──────────────────────────────────────────────
# Standalone Test
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_handler.py <path_to_pdf>")
        sys.exit(1)

    pages, errors = load_pdf_pages(sys.argv[1:])
    print(f"Loaded {len(pages)} pages, {len(errors)} errors")
    for p in pages[:3]:
        print(f"  Page {p['page_num']}: {len(p['text'])} chars")
