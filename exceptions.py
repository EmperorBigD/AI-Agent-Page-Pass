"""
Custom exception hierarchy for the Page Pass AI Agent.

Using specific exception classes allows upstream callers (e.g. main_api.py)
to catch granular errors and return the correct HTTP status codes rather
than a blanket 500 Internal Server Error.
"""


class PagePassError(Exception):
    """Base exception for all Page Pass errors."""
    pass


class ExcelParsingError(PagePassError):
    """Raised when the Excel permissions log is malformed or missing required columns."""
    pass


class PDFExtractionError(PagePassError):
    """Raised when PyMuPDF fails to load or extract text from one or more PDFs."""
    pass


class LLMResponseError(PagePassError):
    """Raised when the Gemini API returns an unparseable or invalid response."""
    pass
