"""
AI audit agent for the Page Pass AI Agent.

Communicates with the Gemini LLM to semantically evaluate whether
the expected credit lines match the text extracted from PDF proofs.
"""

from __future__ import annotations

import asyncio
import json

from google import genai
from google.genai.types import GenerateContentConfig

from config import GEMINI_API_KEY, GEMINI_MODEL_NAME, BATCH_SIZE
from exceptions import LLMResponseError
from schemas import BatchAuditResponse, AuditResult
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from utils import setup_logger, sanitize_llm_json

logger = setup_logger(__name__)

# Initialize client
client = genai.Client(api_key=GEMINI_API_KEY)


# ──────────────────────────────────────────────
# Batch Processing
# ──────────────────────────────────────────────


async def process_batch(batch: list[dict]) -> list[dict]:
    """Send a single batch of assets to the LLM for audit evaluation.

    Assets with status ``"Unfound"`` are excluded from the LLM call and
    passed through unchanged.

    Args:
        batch: A list of asset dictionaries (max :data:`config.BATCH_SIZE`).

    Returns:
        A list of audit result dictionaries combining LLM responses and
        any unfound passthrough assets.
    """
    # Separate unfound assets (no LLM call needed)
    to_process: list[dict] = []
    unfound: list[dict] = []

    for asset in batch:
        if asset.get("status") == "Unfound":
            unfound.append(asset)
        else:
            to_process.append(asset)

    if not to_process:
        logger.debug("Batch contains only unfound assets — skipping LLM call")
        return unfound

    prompt = USER_PROMPT_TEMPLATE.format(batch_json=json.dumps(to_process, indent=2))

    try:
        logger.info(
            "Sending batch of %d assets to %s", len(to_process), GEMINI_MODEL_NAME
        )
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
            config=GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=BatchAuditResponse,
            ),
        )

        response_json = sanitize_llm_json(response.text)
        llm_results = response_json.get("results", [])
        logger.info("LLM returned %d results", len(llm_results))

        return llm_results + unfound

    except LLMResponseError:
        # Already logged inside sanitize_llm_json
        raise

    except Exception as e:
        logger.error("Gemini API error: %s", e)
        # Graceful fallback: mark every asset in this batch as Error
        fallback: list[dict] = []
        for asset in to_process:
            asset["status"] = "Error"
            asset["reasoning"] = str(e)
            fallback.append(asset)
        return fallback + unfound


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


async def run_audit_batch(assets: list[dict]) -> list[dict]:
    """Group extracted PDF windows into batches and run concurrent LLM audits.

    Args:
        assets: The full list of assets with ``extracted_pdf_text`` populated
            by the PDF extraction pipeline.

    Returns:
        A flat list of audit result dictionaries.
    """
    batches = [assets[i : i + BATCH_SIZE] for i in range(0, len(assets), BATCH_SIZE)]
    logger.info("Starting audit: %d assets in %d batch(es)", len(assets), len(batches))

    tasks = [process_batch(batch) for batch in batches]
    results = await asyncio.gather(*tasks)

    # Flatten
    flattened: list[dict] = []
    for batch_res in results:
        for item in batch_res:
            if isinstance(item, AuditResult):
                flattened.append(item.model_dump())
            elif isinstance(item, dict):
                flattened.append(item)
            else:
                flattened.append(dict(item))

    logger.info("Audit complete: %d total results", len(flattened))
    return flattened


# ──────────────────────────────────────────────
# Standalone Test
# ──────────────────────────────────────────────

if __name__ == "__main__":
    sample = [
        {
            "spec": "Figure 1.1",
            "expected_credit": "permission of Springer Nature / CC BY 4.0",
            "description": "Sample figure for testing",
            "extracted_pdf_text": "Figure 1.1 shows ... permission of Springer Nature / CC BY 4.0 ...",
            "status": "Found (Tier 1)",
        }
    ]
    result = asyncio.run(run_audit_batch(sample))
    for r in result:
        print(f"  {r.get('spec'):20s} | {r.get('status')}")
