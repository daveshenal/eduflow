import logging
import json

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
        raise ValueError("No active prompt found for 'main_prompt'. Activate a version via /prompts/activate.")
    if not pdf_prompt_resp:
        raise ValueError("No active prompt found for 'pdf_generator'. Activate a version via /prompts/activate.")
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
    else:
        return {
            'title': "N/A",
            'main_focus': "N/A", 
            'key_concepts': "N/A"
        }


def format_pdf_prompt(template: str, plan_result: dict, doc: dict, 
                        prev_doc: dict, min_words: int, max_words: int, duration: int,
                        doc_id: int, total_docs: int) -> str:
    """Format pdf generation prompt."""
    try:
        # Determine if this is first or last document
        is_first_or_last = doc_id == 1 or doc_id == total_docs
        
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
        error_msg = f"Template formatting error - missing placeholder in pdf prompt: {ke}"
        logging.error(error_msg)
        raise ValueError(error_msg)


async def generate_single_doc(claude_client, system_prompt: str, user_messages: list) -> dict:
    """Generate content for a single document."""
    response = await claude_client.messages.create(
        model=settings.CLAUDE_MODEL_DOC,
        max_tokens=settings.MAX_TOKEN,
        system=system_prompt,
        temperature=0.3,
        messages=user_messages,
    )
    
    # Log usage
    usage = response.usage
    logging.info(f"Document tokens — Input: {usage.input_tokens}, Output: {usage.output_tokens}")
    
    # Extract content
    doc_parts = []
    for block in getattr(response, "content", []) or []:
        if isinstance(block, dict):
            doc_parts.append(block.get("text", ""))
        else:
            doc_parts.append(getattr(block, "text", ""))
    
    content = "".join(doc_parts).strip()
    
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
    Generate and return the HTML content for a single doc.
    """
    title = doc.get("title")
    main_focus = doc.get("main_focus")
    retrieval_query = (doc.get("retrieval_query") or "") + " " + " ".join([p for p in [title, main_focus] if p])

    # Fetch context from knowledge base (single AI index)
    retrieved_docs = retriever.get_relevant_documents(query=retrieval_query.strip())
    context = retriever.format_context_with_sources(retrieved_docs)
    
    # Get previous doc info
    prev_doc = get_previous_doc_info(docs, doc_id)
    
    # Format doc prompt
    doc_details = format_pdf_prompt(
        prompts['doc_prompt'], plan_result, doc, prev_doc,
        min_words, max_words, duration, doc_id, len(docs)
    )
    
    user_messages = [
        {"role": "user", "content": f"DOCUMENT DETAILS (from plan):\n{doc_details}"},
        {"role": "user", "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}"},
        {"role": "user", "content": "Generate the full document content now."},
    ]
    
    # Generate and return doc content
    doc_result = await generate_single_doc(claude_client, prompts['system_prompt'], user_messages)
    
    return {
        "doc_id": doc_id,
        "title": title,
        "content_html": doc_result["content"],
        "tokens": doc_result["tokens"]
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
        f"""
        Target length: {min_words}–{max_words} words. Duration: {duration} minutes.

        Output the entire document content using raw HTML tags: <h1>, <h2>, <h3>, <p>, <ul>, <li>, <strong>, <a>.
        Do NOT use Markdown or any other formatting.
        Exclude <html>, <body>, or <pre> wrappers.
        Wrap all standalone text and paragraphs in <p> tags for proper readability.

        Endnote Citations: When referencing a source, place the citation number in superscript in the top-right of the last letter of the referenced text. This should be done by wrapping the citation number in a <sup> tag (e.g., "as shown in recent studies<sup>[1]</sup>"). Ensure the number appears small and in the correct position.
        Sources Section: At the end of the content, list all sources in the following format:
        Numbered list: [1] Source name, [2] Source name, etc.
        Ensure that the sources are listed in the order they were referenced in the document.
        """
    )
    user_messages = [
        {"role": "user", "content": f"REQUEST:\n{user_prompt}\n\nCONSTRAINTS:\n{constraints}"},
        {"role": "user", "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}"},
        {"role": "user", "content": "Generate the full document content now (HTML)."},
    ]

    doc_result = await generate_single_doc(
        claude_client, prompts["system_prompt"], user_messages
    )
    return {
        "doc_id": doc_id,
        "title": f"Document {doc_id}",
        "content_html": doc_result["content"],
        "tokens": doc_result["tokens"],
    }


async def process_single_doc_memory(
    claude_client,
    user_prompt: str,
    doc_id: int,
    retriever,
    prompts: dict,
    min_words: int,
    max_words: int,
    duration: int,
    memory_summary: str,
) -> dict:
    """
    Memory workflow: generate one doc from user prompt + retrieval using that same prompt as query,
    plus a running summary of all previous docs.
    """
    retrieved_docs = retriever.get_relevant_documents(query=user_prompt.strip())
    context = retriever.format_context_with_sources(retrieved_docs)

    constraints = (
        f"""
        Target length: {min_words}–{max_words} words. Duration: {duration} minutes.

        Output the entire document content using raw HTML tags: <h1>, <h2>, <h3>, <p>, <ul>, <li>, <strong>, <a>.
        Do NOT use Markdown or any other formatting.
        Exclude <html>, <body>, or <pre> wrappers.
        Wrap all standalone text and paragraphs in <p> tags for proper readability.

        Endnote Citations: When referencing a source, place the citation number in superscript in the top-right of the last letter of the referenced text. This should be done by wrapping the citation number in a <sup> tag (e.g., "as shown in recent studies<sup>[1]</sup>"). Ensure the number appears small and in the correct position.
        Sources Section: At the end of the content, list all sources in the following format:
        Numbered list: [1] Source name, [2] Source name, etc.
        Ensure that the sources are listed in the order they were referenced in the document.
        """
    )

    messages = []
    if memory_summary:
        messages.append(
            {
                "role": "user",
                "content": f"MEMORY (summary of previous docs):\n{memory_summary}",
            }
        )

    messages.extend(
        [
            {
                "role": "user",
                "content": f"REQUEST:\n{user_prompt}\n\nCONSTRAINTS:\n{constraints}",
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
        claude_client, prompts["system_prompt"], messages
    )
    return {
        "doc_id": doc_id,
        "title": f"Document {doc_id}",
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
        "You are a summarization assistant that maintains a concise running summary of a learning sequence. "
        "Keep key topics, concepts, and progression, in at most "
        f"{max_words} words. The summary will be used as memory when generating subsequent docs."
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
