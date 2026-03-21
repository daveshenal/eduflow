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
from pydantic import BaseModel, Field

from evaluator_service.evaluators.document_evaluator import evaluate_documents
from evaluator_service.metrics.pairwise_judge import PairwiseJudge

router = APIRouter(prefix="/evaluate", tags=["evaluation"])

MAX_FILES = 10
DEFAULT_PAIRWISE_CRITERIA = [
    "coherence",
    "dependency_flow",
    "content_progression",
    "non_redundancy",
]


class PairwiseSequenceInput(BaseModel):
    architecture: str
    documents: list[str] = Field(default_factory=list)


class PairwiseEvaluateRequest(BaseModel):
    sequence_a: PairwiseSequenceInput
    sequence_b: PairwiseSequenceInput
    criteria: list[str] = Field(default_factory=lambda: DEFAULT_PAIRWISE_CRITERIA.copy())
    runs: int = Field(default=3, ge=1)


class PairwiseRunDetail(BaseModel):
    run: int
    order_shown: list[str]
    winner: str
    reasoning: str
    criteria_scores: dict = Field(default_factory=dict)


class PairwiseEvaluateResponse(BaseModel):
    winner: str
    win_counts: dict[str, int]
    win_rate: dict[str, float]
    run_details: list[PairwiseRunDetail]
    consensus: str


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


@router.post("/pairwise", response_model=PairwiseEvaluateResponse)
async def evaluate_pairwise(payload: PairwiseEvaluateRequest):
    """
    POST /evaluate/pairwise - Compare two document sequences using an LLM judge.
    """
    if not payload.sequence_a.documents or not payload.sequence_b.documents:
        raise HTTPException(
            status_code=400,
            detail="Both sequence_a.documents and sequence_b.documents must be provided.",
        )

    judge = PairwiseJudge()
    try:
        result = judge.run_evaluation(
            sequence_a=payload.sequence_a.model_dump(),
            sequence_b=payload.sequence_b.model_dump(),
            criteria=payload.criteria or DEFAULT_PAIRWISE_CRITERIA,
            runs=payload.runs,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pairwise evaluation failed: {str(e)}")

    return result
