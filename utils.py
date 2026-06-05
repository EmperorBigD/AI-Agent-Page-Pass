"""
Shared utility functions for the Page Pass AI Agent.

Contains reusable helpers that are consumed by multiple modules,
keeping business-logic files focused on their own responsibilities.
"""

import json
import re
import logging

from exceptions import LLMResponseError


def setup_logger(name: str) -> logging.Logger:
    """Create and configure a logger with a consistent format.

    Args:
        name: The logger name, typically ``__name__`` of the calling module.

    Returns:
        A configured ``logging.Logger`` instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    return logger


def sanitize_llm_json(raw_text: str) -> dict:
    """Extract and decode a JSON object from raw LLM output.

    The LLM may wrap its response in markdown fences, include conversational
    preamble, or produce invalid backslash escape sequences.  This function
    handles all of those cases and returns a parsed Python ``dict``.

    Args:
        raw_text: The raw ``response.text`` string from the Gemini API.

    Returns:
        The parsed JSON object as a Python dictionary.

    Raises:
        LLMResponseError: If JSON extraction or decoding fails after all
            sanitization attempts.
    """
    # Step 1: Try to find JSON inside markdown code blocks
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if match:
        clean_text = match.group(1)
    else:
        # Step 2: Fallback — extract between first { and last }
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1:
            clean_text = raw_text[start : end + 1]
        else:
            clean_text = raw_text

    # Step 3: Fix invalid backslash escapes (e.g. malformed \uXXXX or \c)
    # Escapes any backslash NOT followed by a valid JSON escape sequence.
    clean_text = re.sub(
        r'\\(?![/"\\bfnrt]|u[0-9a-fA-F]{4})', r"\\\\", clean_text
    )

    # Step 4: Decode
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        raise LLMResponseError(
            f"Failed to decode LLM JSON response: {e}\nSanitized text: {clean_text[:500]}"
        ) from e
