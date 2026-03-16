"""
CREATE API router
DEFINE POST endpoint "/evaluate"
Accept multiple PDFs (max 10)
Validate input
Send files to document_evaluator
Return evaluation results as JSON
"""

import tempfile
import os
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException

from evaluator_service.evaluators.document_evaluator import evaluate_documents

router = APIRouter(prefix="/evaluate", tags=["evaluation"])

MAX_FILES = 10


@router.post("")
async def evaluate(
    files: list[UploadFile] = File(..., description="PDF files to evaluate (max 10)"),
):
    """
    POST /evaluate - Accept up to 10 PDF files and return evaluation metrics.
    """
    # VALIDATE: if number_of_files > 10 return error
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum allowed is {MAX_FILES}.",
        )

    # Validate all files are PDFs
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. All files must be PDF: {f.filename}",
            )

    # FOR each uploaded file save file temporarily
    temp_paths: list[str] = []
    try:
        for upload_file in files:
            content = await upload_file.read()
            if len(content) == 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Empty or invalid PDF: {upload_file.filename}",
                )
            # Save to temp file
            suffix = Path(upload_file.filename or "doc.pdf").suffix
            fd, path = tempfile.mkstemp(suffix=suffix)
            try:
                with os.fdopen(fd, "wb") as tmp:
                    tmp.write(content)
                temp_paths.append(path)
            except Exception:
                os.close(fd)
                raise

        # SEND saved file paths to document_evaluator
        results = evaluate_documents(temp_paths)

        # RETURN results as JSON
        return results

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        # Clean up temp files
        for path in temp_paths:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except OSError:
                pass
