import os
import json
import asyncio
import re
from google import genai
from google.genai.types import GenerateContentConfig
from dotenv import load_dotenv

from schemas import BatchAuditResponse, AuditResult
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

# Load API key from .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Initialize client (it automatically picks up GEMINI_API_KEY from environment if passed,
# but we can explicitly pass it as well)
client = genai.Client(api_key=api_key)


async def process_batch(batch: list[dict]) -> list[dict]:
    """Process a single batch of up to 20 assets."""
    # Filter out 'Unfound' assets as they don't need LLM processing
    to_process = []
    unfound = []

    for asset in batch:
        if asset.get("status") == "Unfound":
            unfound.append(asset)
        else:
            to_process.append(asset)

    if not to_process:
        return unfound

    prompt = USER_PROMPT_TEMPLATE.format(batch_json=json.dumps(to_process, indent=2))

    try:
        response = await client.aio.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=BatchAuditResponse,
            ),
        )

        raw_text = response.text

        # Robust JSON extraction
        # Try to find JSON inside markdown blocks
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if match:
            clean_text = match.group(1)
        else:
            # Fallback: extract between first { and last }
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end != -1:
                clean_text = raw_text[start : end + 1]
            else:
                clean_text = raw_text

        # Robust cleanup for invalid backslash escapes (e.g. invalid \uXXXX or \c)
        # This finds any backslash that is NOT followed by a valid JSON escape sequence
        # (", \, /, b, f, n, r, t, or u + 4 hex digits) and escapes it.
        clean_text = re.sub(r'\\(?![/"\\bfnrt]|u[0-9a-fA-F]{4})', r"\\\\", clean_text)

        try:
            response_json = json.loads(clean_text)
        except json.JSONDecodeError as decode_error:
            print(f"Failed to decode JSON: {decode_error}")
            print(f"Raw text was: {raw_text}")
            raise

        # Merge LLM results back with any unfound items
        llm_results = response_json.get("results", [])

        return llm_results + unfound

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # Fallback in case of error: mark everything as 'Error'
        fallback_results = []
        for asset in to_process:
            asset["status"] = "Error"
            asset["reasoning"] = str(e)
            fallback_results.append(asset)
        return fallback_results + unfound


async def run_audit_batch(assets: list[dict]) -> list[dict]:
    """Group extracted PDF windows into batches and execute concurrent requests."""
    batch_size = 20
    batches = [assets[i : i + batch_size] for i in range(0, len(assets), batch_size)]

    tasks = [process_batch(batch) for batch in batches]

    # Run all batches concurrently
    results = await asyncio.gather(*tasks)

    # Flatten the list of lists
    flattened_results = []
    for batch_res in results:
        for item in batch_res:
            if isinstance(item, AuditResult):
                flattened_results.append(item.model_dump())
            elif isinstance(item, dict):
                flattened_results.append(item)
            else:
                flattened_results.append(dict(item))

    return flattened_results
