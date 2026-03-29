"""PDF and HTML document generation via Claude: plan-based, baseline, and memory flows."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from config.settings import settings
from app.prompts.prompt_management import get_prompt_manager, PromptNames


async def fetch_pdf_prompts(db_conn) -> dict:
    """
    Load PDF/document-generation prompts from the prompt manager (DB).
    Uses active prompts: main_prompt (system), pdf_generator (doc_prompt).
    Returns dict with system_prompt and doc_prompt.
    """
    manager = get_prompt_manager()
    system_prompt_resp = await manager.get_active_prompt(PromptNames.MAIN_PROMPT.value, db_conn)
    pdf_prompt_resp = await manager.get_active_prompt(PromptNames.PDF_GENERATOR.value, db_conn)
    if not system_prompt_resp:
        raise ValueError(
            "No active prompt found for 'main_prompt'. Activate a version via /prompts/activate.")
    if not pdf_prompt_resp:
        raise ValueError(
            "No active prompt found for 'pdf_generator'. Activate a version via /prompts/activate.")
    return {
        "system_prompt": system_prompt_resp.prompt,
        "doc_prompt": pdf_prompt_resp.prompt,
    }


def get_previous_doc_info(docs: list, doc_id: int) -> dict:
    """Get previous document information for context."""
    if doc_id > 1:
        prev_doc = docs[doc_id - 2]
        return {
            'title': prev_doc.get("title", "N/A"),
            'main_focus': prev_doc.get("main_focus", "N/A"),
            'key_concepts': ", ".join(prev_doc.get("key_concepts", [])) or "N/A"
        }
    return {
        'title': "N/A",
        'main_focus': "N/A",
        'key_concepts': "N/A"
    }


@dataclass
class PdfPromptFormatParams:
    """Inputs for filling the PDF generation prompt template."""
    template: str
    plan_result: dict
    doc: dict
    prev_doc: dict
    min_words: int
    max_words: int
    duration: int
    doc_id: int
    total_docs: int


def format_pdf_prompt(params: PdfPromptFormatParams) -> str:
    """Format the PDF user prompt from plan, doc, and neighbor context."""
    try:
        is_first_or_last = params.doc_id == 1 or params.doc_id == params.total_docs

        if is_first_or_last:
            complete_curriculum = json.dumps(params.plan_result, indent=2)
        else:
            complete_curriculum = "N/A"

        meta = params.plan_result.get("curriculum_metadata")
        target_audience = meta.get("target_audience")
        return params.template.format(
            curriculum_title=meta.get("title", ""),
            target_audience=target_audience,
            doc_type=params.doc.get("type"),
            title=params.doc.get("title"),
            main_focus=params.doc.get("main_focus"),
            key_concepts=params.doc.get("key_concepts"),
            learning_outcome=params.doc.get("learning_outcome"),
            builds_on=params.doc.get("builds_on"),
            sets_up=params.doc.get("sets_up"),
            min_words=params.min_words,
            max_words=params.max_words,
            duration=f"{params.duration} minutes",
            previous_doc_title=params.prev_doc['title'],
            previous_main_focus=params.prev_doc['main_focus'],
            previous_key_concepts=params.prev_doc['key_concepts'],
            complete_curriculum=complete_curriculum
        )
    except KeyError as ke:
        error_msg = f"Template formatting error - missing placeholder in pdf prompt: {ke}"
        logging.error(error_msg)
        raise ValueError(error_msg) from ke


def _baseline_style_html_constraints(min_words: int, max_words: int, duration: int) -> str:
    """Shared HTML/output constraints for baseline and memory single-doc generation."""
    return (
        f"""
        Target length: {min_words}–{max_words} words. Duration: {duration} minutes.

        Output the entire document content using raw HTML tags: <h1>, <h2>, <h3>, <p>, """
        f"""<ul>, <li>, <strong>, <a>.
        Do NOT use Markdown or any other formatting.
        Exclude <html>, <body>, or <pre> wrappers.
        Wrap all standalone text and paragraphs in <p> tags for proper readability.

        Endnote Citations: When referencing a source, place the citation number in """
        """superscript in the top-right of the last letter of the referenced text. """
        """This should be done by wrapping the citation number in a <sup> tag (e.g., """
        """"as shown in recent studies<sup>[1]</sup>"). Ensure the number appears small """
        """and in the correct position.
        Sources Section: At the end of the content, list all sources in the following """
        """format:
        Numbered list: [1] Source name, [2] Source name, etc.
        Ensure that the sources are listed in the order they were referenced in the """
        """document.
        """
    )


async def generate_single_doc(claude_client, system_prompt: str, user_messages: list) -> dict:
    """Generate content for a single document."""
    response = await claude_client.messages.create(
        model=settings.CLAUDE_MODEL_DOC,
        max_tokens=settings.MAX_TOKEN,
        system=system_prompt,
        temperature=0.3,
        messages=user_messages,
    )

    usage = response.usage
    logging.info(
        "Document tokens — Input: %s, Output: %s",
        usage.input_tokens,
        usage.output_tokens,
    )

    doc_parts = []
    for block in getattr(response, "content", []) or []:
        if isinstance(block, dict):
            doc_parts.append(block.get("text", ""))
        else:
            doc_parts.append(getattr(block, "text", ""))

    content = "".join(doc_parts).strip()

    return {
        "content": content,
        "tokens": {
            "input": usage.input_tokens,
            "output": usage.output_tokens
        }
    }


@dataclass
class PlanBasedDocParams:
    """Retrieval + plan context for generating one curriculum doc."""
    doc: dict
    doc_id: int
    plan_result: dict
    docs: list
    retriever: Any
    prompts: dict
    min_words: int
    max_words: int
    duration: int


async def process_single_doc(claude_client, params: PlanBasedDocParams):
    """Generate and return the HTML content for a single plan-driven doc."""
    title = params.doc.get("title")
    main_focus = params.doc.get("main_focus")
    retrieval_query = (
        (params.doc.get("retrieval_query") or "")
        + " "
        + " ".join([p for p in [title, main_focus] if p])
    )

    retrieved_docs = params.retriever.get_relevant_documents(
        query=retrieval_query.strip())
    context = params.retriever.format_context_with_sources(retrieved_docs)

    prev_doc = get_previous_doc_info(params.docs, params.doc_id)

    doc_details = format_pdf_prompt(
        PdfPromptFormatParams(
            template=params.prompts['doc_prompt'],
            plan_result=params.plan_result,
            doc=params.doc,
            prev_doc=prev_doc,
            min_words=params.min_words,
            max_words=params.max_words,
            duration=params.duration,
            doc_id=params.doc_id,
            total_docs=len(params.docs),
        )
    )

    user_messages = [
        {"role": "user",
            "content": f"DOCUMENT DETAILS (from plan):\n{doc_details}"},
        {"role": "user", "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}"},
        {"role": "user", "content": "Generate the full document content now."},
    ]

    doc_result = await generate_single_doc(
        claude_client, params.prompts['system_prompt'], user_messages)

    return {
        "doc_id": params.doc_id,
        "title": title,
        "content_html": doc_result["content"],
        "tokens": doc_result["tokens"]
    }


@dataclass
class BaselineDocParams:
    """User prompt + retrieval settings for one baseline (no-plan) doc."""
    user_prompt: str
    doc_id: int
    retriever: Any
    prompts: dict
    min_words: int
    max_words: int
    duration: int


async def process_single_doc_baseline(
    claude_client,
    params: BaselineDocParams,
) -> dict:
    """
    Baseline: generate one doc from user prompt + retrieval using that same prompt as query.
    Uses minimal system prompt + user prompt + retrieved context. No curriculum plan.
    """
    retrieved_docs = params.retriever.get_relevant_documents(
        query=params.user_prompt.strip())
    context = params.retriever.format_context_with_sources(retrieved_docs)

    constraints = _baseline_style_html_constraints(
        params.min_words, params.max_words, params.duration
    )
    user_messages = [
        {"role": "user",
         "content": f"REQUEST:\n{params.user_prompt}\n\nCONSTRAINTS:\n{constraints}"},
        {"role": "user", "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}"},
        {"role": "user",
            "content": "Generate the full document content now (HTML)."},
    ]

    doc_result = await generate_single_doc(
        claude_client, params.prompts["system_prompt"], user_messages
    )
    return {
        "doc_id": params.doc_id,
        "title": f"Document {params.doc_id}",
        "content_html": doc_result["content"],
        "tokens": doc_result["tokens"],
    }


@dataclass
class MemoryDocParams:
    """Baseline params plus optional memory summary from prior docs."""
    user_prompt: str
    doc_id: int
    retriever: Any
    prompts: dict
    min_words: int
    max_words: int
    duration: int
    memory_summary: str


async def process_single_doc_memory(
    claude_client,
    params: MemoryDocParams,
) -> dict:
    """
    Memory workflow: generate one doc from user prompt + retrieval using that same prompt
    as query, plus a running summary of all previous docs.
    """
    retrieved_docs = params.retriever.get_relevant_documents(
        query=params.user_prompt.strip())
    context = params.retriever.format_context_with_sources(retrieved_docs)

    constraints = _baseline_style_html_constraints(
        params.min_words, params.max_words, params.duration
    )

    messages = []
    if params.memory_summary:
        messages.append(
            {
                "role": "user",
                "content": f"MEMORY (summary of previous docs):\n{params.memory_summary}",
            }
        )

    messages.extend(
        [
            {
                "role": "user",
                "content": f"REQUEST:\n{params.user_prompt}\n\nCONSTRAINTS:\n{constraints}",
            },
            {
                "role": "user",
                "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}",
            },
            {
                "role": "user",
                "content": "Generate the full document content now (HTML).",
            },
        ]
    )

    doc_result = await generate_single_doc(
        claude_client, params.prompts["system_prompt"], messages
    )
    return {
        "doc_id": params.doc_id,
        "title": f"Document {params.doc_id}",
        "content_html": doc_result["content"],
        "tokens": doc_result["tokens"],
    }


async def update_memory_summary(
    claude_client,
    previous_summary: str,
    new_doc_html: str,
    max_words: int = 400,
) -> dict:
    """
    Update the running memory summary with the latest doc.
    Returns dict with `summary` and `tokens`.
    """
    base_system_prompt = (
        "You are a summarization assistant that maintains a concise running summary "
        "of a learning sequence. "
        "Keep key topics, concepts, and progression, in at most "
        f"{max_words} words. The summary will be used as memory when generating "
        "subsequent docs."
    )

    user_parts = []
    if previous_summary:
        user_parts.append(f"PREVIOUS SUMMARY:\n{previous_summary}")
    user_parts.append(f"LATEST DOCUMENT (HTML):\n{new_doc_html}")
    user_parts.append("Update the running summary.")

    messages = [{"role": "user", "content": "\n\n".join(user_parts)}]

    response = await claude_client.messages.create(
        model=settings.CLAUDE_MODEL_DOC,
        max_tokens=settings.MAX_TOKEN,
        system=base_system_prompt,
        temperature=0.3,
        messages=messages,
    )

    usage = response.usage
    logging.info(
        "Memory summary tokens — Input: %s, Output: %s",
        usage.input_tokens,
        usage.output_tokens,
    )

    parts = []
    for block in getattr(response, "content", []) or []:
        if isinstance(block, dict):
            parts.append(block.get("text", ""))
        else:
            parts.append(getattr(block, "text", ""))
    summary_text = "".join(parts).strip()

    return {
        "summary": summary_text,
        "tokens": {
            "input": usage.input_tokens,
            "output": usage.output_tokens,
        },
    }
