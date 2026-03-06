"""
PDF text extraction utility.
Uses PyPDF2 to extract text from PDF files.
"""

from pathlib import Path

import PyPDF2


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a single PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text as a single string.

    Raises:
        FileNotFoundError: If PDF file does not exist.
        ValueError: If PDF is invalid or cannot be read.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Invalid file type. Expected PDF: {pdf_path}")

    try:
        reader = PyPDF2.PdfReader(pdf_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts) if text_parts else ""
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF {pdf_path}: {str(e)}") from e
