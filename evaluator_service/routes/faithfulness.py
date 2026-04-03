"""
POST /eval/faithfulness — synchronous faithfulness scoring for downloaded job artifacts.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from evaluator_service.evaluators.faithfulness_evaluator import compute_faithfulness

router = APIRouter(prefix="/evaluate", tags=["faithfulness"])


class FaithfulnessRequest(BaseModel):
    job_id: str = Field(..., min_length=1, description="Job folder id, e.g. job-1774534470161")
    index_id: str = Field(..., min_length=1, description="Knowledge base index id (Azure ai-index-{index_id})")
    use_input_param_queries: bool = Field(
        default=False,
        description=(
            "False: EduFlow — retrieval query from each plan.doc (retrieval_query + title + main_focus). "
            "True: baseline & memory — each query from logs/input_params.json prompts[i] for doc i+1."
        ),
    )


class ChunkUsed(BaseModel):
    source_name: str = ""
    text: str = ""


class FaithfulnessSessionOut(BaseModel):
    session_index: int
    title: str
    faithfulness_score: int
    reasoning: str
    claim_count: int = Field(description="Substantive claims identified in the document (LLM count).")
    supported_claim_count: int = Field(
        description="Claims judged supported by retrieved context (<= claim_count).",
    )
    chunks_used: list[ChunkUsed]
    low_faithfulness: bool


class FaithfulnessResponse(BaseModel):
    job_id: str
    index_id: str
    use_input_param_queries: bool
    overall_faithfulness_score: float
    total_claims: int = Field(description="Sum of claim_count across sessions.")
    total_supported_claims: int = Field(description="Sum of supported_claim_count across sessions.")
    overall_supported_claim_ratio: float | None = Field(
        default=None,
        description="total_supported_claims / total_claims when total_claims > 0.",
    )
    sessions: list[FaithfulnessSessionOut]


@router.post("/faithfulness", response_model=FaithfulnessResponse)
async def faithfulness_score(payload: FaithfulnessRequest):
    """
    Load plan + PDFs from eval_results/downloaded_jobs, re-run retrieval with the same
    settings as generation, and score grounding vs retrieved chunks per session.
    """
    try:
        result = compute_faithfulness(
            payload.job_id,
            payload.index_id,
            use_input_param_queries=payload.use_input_param_queries,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Faithfulness scoring failed: {str(e)}"
        ) from e

    return result
