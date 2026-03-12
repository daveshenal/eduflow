"""
IMPORT pdf loader utility
IMPORT coherence metric
FUNCTION evaluate_documents(pdf_file_paths)
  Extract text from PDFs
  Ensure documents remain in correct order
  Call metrics (currently only coherence)
  Aggregate results
  Return dictionary with results
"""

from utils.pdf_extractor import extract_text_from_pdf
from metrics.coherence import calculate_coherence


def evaluate_documents(pdf_file_paths: list[str]) -> dict:
    """
    Evaluate documents from PDF file paths.
    Documents are processed in the order given.
    """
    # INITIALIZE empty list documents
    documents: list[str] = []

    # FOR each pdf in pdf_file_paths
    for pdf_path in pdf_file_paths:
        # text = extract_text_from_pdf(pdf)
        text = extract_text_from_pdf(pdf_path)
        if not (text or "").strip():
            raise ValueError(f"PDF contains no extractable text: {pdf_path}")
        # append text to documents list
        documents.append(text.strip())

    # ENSURE documents remain in correct order (already in order by iteration)

    # Metric Calculations - currently only coherence
    coherence_score = calculate_coherence(documents)

    # CREATE results dictionary
    results: dict = {
        "document_count": len(documents),
        "metrics": {
            "coherence": coherence_score,
        },
    }

    return results
