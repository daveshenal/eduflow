import logging
import json

from config.settings import settings
from app.prompts.prompt_management import get_prompt_manager, PromptNames


async def fetch_pdf_prompts(db_conn) -> dict:
    """
    Load PDF/document-generation prompts from the prompt manager (DB).
    Uses active prompts: main_prompt (system), pdf_generator (huddle_prompt).
    Returns dict with system_prompt and huddle_prompt.
    """
    manager = get_prompt_manager()
    system_prompt_resp = await manager.get_active_prompt(PromptNames.MAIN_PROMPT.value, db_conn)
    pdf_prompt_resp = await manager.get_active_prompt(PromptNames.PDF_GENERATOR.value, db_conn)
    if not system_prompt_resp:
        raise ValueError("No active prompt found for 'main_prompt'. Activate a version via /prompts/activate.")
    if not pdf_prompt_resp:
        raise ValueError("No active prompt found for 'pdf_generator'. Activate a version via /prompts/activate.")
    return {
        "system_prompt": system_prompt_resp.prompt,
        "huddle_prompt": pdf_prompt_resp.prompt,
    }


def get_previous_doc_info(huddles: list, huddle_id: int) -> dict:
    """Get previous huddle information for context."""
    if huddle_id > 1:
        prev_huddle = huddles[huddle_id - 2]
        return {
            'title': prev_huddle.get("title", "N/A"),
            'main_focus': prev_huddle.get("main_focus", "N/A"),
            'key_concepts': ", ".join(prev_huddle.get("key_concepts", [])) or "N/A"
        }
    else:
        return {
            'title': "N/A",
            'main_focus': "N/A", 
            'key_concepts': "N/A"
        }


def format_pdf_prompt(template: str, plan_result: dict, doc: dict, 
                        prev_doc: dict, min_words: int, max_words: int, duration: int,
                        doc_id: int, total_huddles: int) -> str:
    """Format pdf generation prompt."""
    try:
        # Determine if this is first or last huddle
        is_first_or_last = doc_id == 1 or doc_id == total_huddles
        
        # Convert dict to JSON string for template formatting
        if is_first_or_last:
            complete_curriculum = json.dumps(plan_result, indent=2)
        else:
            complete_curriculum = "N/A"
        
        meta = plan_result.get("curriculum_metadata")
        target_audience = meta.get("target_audience")
        return template.format(
            curriculum_title=meta.get("title", ""),
            target_audience=target_audience,
            doc_type=doc.get("type"),
            title=doc.get("title"),
            main_focus=doc.get("main_focus"),
            key_concepts=doc.get("key_concepts"),
            learning_outcome=doc.get("learning_outcome"),
            builds_on=doc.get("builds_on"),
            sets_up=doc.get("sets_up"),
            min_words=min_words,
            max_words=max_words,
            duration=f"{duration} minutes",
            previous_doc_title=prev_doc['title'],
            previous_main_focus=prev_doc['main_focus'],
            previous_key_concepts=prev_doc['key_concepts'],
            complete_curriculum=complete_curriculum
        )
    except KeyError as ke:
        error_msg = f"Template formatting error - missing placeholder in huddle prompt: {ke}"
        logging.error(error_msg)
        raise ValueError(error_msg)


async def generate_single_doc(claude_client, system_prompt: str, user_messages: list) -> dict:
    """Generate content for a single huddle."""
    huddle_response = await claude_client.messages.create(
        model=settings.CLAUDE_MODEL_HUDDLE,
        max_tokens=settings.MAX_TOKEN,
        system=system_prompt,
        temperature=0.3,
        messages=user_messages,
    )
    
    # Log usage
    usage = huddle_response.usage
    logging.info(f"Huddle tokens — Input: {usage.input_tokens}, Output: {usage.output_tokens}")
    
    # Extract huddle content
    huddle_parts = []
    for block in getattr(huddle_response, "content", []) or []:
        if isinstance(block, dict):
            huddle_parts.append(block.get("text", ""))
        else:
            huddle_parts.append(getattr(block, "text", ""))
    
    content = "".join(huddle_parts).strip()
    
    # Return both content and token usage
    return {
        "content": content,
        "tokens": {
            "input": usage.input_tokens,
            "output": usage.output_tokens
        }
    }


async def process_single_doc(claude_client, doc: dict, doc_id: int, plan_result: dict,
                             docs: list, retriever, prompts: dict, min_words: int, max_words: int,
                             duration: int):
    """
    Generate and return the HTML content for a single doc/huddle.
    """
    title = doc.get("title")
    main_focus = doc.get("main_focus")
    retrieval_query = (doc.get("retrieval_query") or "") + " " + " ".join([p for p in [title, main_focus] if p])

    # Fetch context from knowledge base (single AI index)
    retrieved_docs = retriever.get_relevant_documents(query=retrieval_query.strip())
    context = retriever.format_context_with_sources(retrieved_docs)
    
    # Get previous huddle info
    prev_huddle = get_previous_doc_info(docs, doc_id)
    
    # Format huddle prompt
    huddle_details = format_pdf_prompt(
        prompts['huddle_prompt'], plan_result, doc, prev_huddle,
        min_words, max_words, duration, doc_id, len(docs)
    )
    
    user_messages = [
        {"role": "user", "content": f"HUDDLE DETAILS (from plan):\n{huddle_details}"},
        {"role": "user", "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}"},
        {"role": "user", "content": "Generate the full Huddle content now."},
    ]
    
    # Generate and return huddle content
    huddle_result = await generate_single_doc(claude_client, prompts['system_prompt'], user_messages)
    
    return {
        "huddle_id": doc_id,
        "title": title,
        "content_html": huddle_result["content"],
        "tokens": huddle_result["tokens"]
    }


async def process_single_doc_baseline(
    claude_client,
    user_prompt: str,
    doc_id: int,
    retriever,
    prompts: dict,
    min_words: int,
    max_words: int,
    duration: int,
) -> dict:
    """
    Baseline: generate one doc from user prompt + retrieval using that same prompt as query.
    Uses minimal system prompt + user prompt + retrieved context. No curriculum plan.
    """
    # Use user prompt as retrieval query
    retrieved_docs = retriever.get_relevant_documents(query=user_prompt.strip())
    context = retriever.format_context_with_sources(retrieved_docs)

    constraints = (
        f"Target length: {min_words}–{max_words} words. Duration: {duration} minutes. "
        "Output well-structured HTML (e.g. headings, paragraphs, lists) suitable for a PDF."
    )
    user_messages = [
        {"role": "user", "content": f"REQUEST:\n{user_prompt}\n\nCONSTRAINTS:\n{constraints}"},
        {"role": "user", "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}"},
        {"role": "user", "content": "Generate the full document content now (HTML)."},
    ]

    huddle_result = await generate_single_doc(
        claude_client, prompts["system_prompt"], user_messages
    )
    return {
        "huddle_id": doc_id,
        "title": f"Document {doc_id}",
        "content_html": huddle_result["content"],
        "tokens": huddle_result["tokens"],
    }