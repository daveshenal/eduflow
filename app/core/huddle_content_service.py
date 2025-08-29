import logging

from config.settings import settings
from app.prompts.prompt_management import get_manager, get_db_connection


async def fetch_huddle_prompts() -> dict:
    """Fetch prompts needed for individual huddle generation."""
    async with get_db_connection() as db_conn:
        prompts_to_fetch = [
            ("main_prompts", "main_prompt", "system_prompt"),
            ("use_case_prompts", "huddle_generator", "huddle_prompt"),
        ]
        
        prompt_vars = {}
        for manager_name, key, var_name in prompts_to_fetch:
            manager = get_manager(manager_name)
            obj = await manager.get_active_prompt(key, db_conn)
            prompt_vars[var_name] = obj.prompt
    
    return prompt_vars


def get_previous_huddle_info(huddles: list, huddle_id: int) -> dict:
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


def format_huddle_prompt(template: str, plan_result: dict, huddle: dict, 
                        prev_huddle: dict, min_words: int, max_words: int, duration: int) -> str:
    """Format huddle generation prompt."""
    try:
        return template.format(
            curriculum_title=plan_result["curriculum_metadata"]["title"],
            target_role=plan_result["curriculum_metadata"]["target_role"],
            discipline=plan_result["curriculum_metadata"]["discipline"],
            huddle_type=huddle.get("type"),
            huddle_title=huddle.get("title"),
            main_focus=huddle.get("main_focus"),
            key_concepts=huddle.get("key_concepts"),
            clinical_scenario=huddle.get("clinical_scenario"),
            learning_outcome=huddle.get("learning_outcome"),
            builds_on=huddle.get("builds_on"),
            sets_up=huddle.get("sets_up"),
            min_words=min_words,
            max_words=max_words,
            duration=f"{duration} minutes",
            previous_huddle_title=prev_huddle['title'],
            previous_main_focus=prev_huddle['main_focus'],
            previous_key_concepts=prev_huddle['key_concepts']
        )
    except KeyError as ke:
        error_msg = f"Template formatting error - missing placeholder in huddle prompt: {ke}"
        logging.error(error_msg)
        raise ValueError(error_msg)


async def generate_single_huddle(claude_client, system_prompt: str, user_messages: list) -> str:
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
    
    return "".join(huddle_parts).strip()


async def process_single_huddle(claude_client, huddle: dict, huddle_id: int, plan_result: dict, 
                               huddles: list, retriever, prompts: dict, min_words: int, max_words: int,
                               duration: int):
    """Generate and return the HTML content for a single huddle.
    """
    title = huddle.get("title")
    main_focus = huddle.get("main_focus")
    retrieval_query = huddle.get("retrieval_query") + " " + " ".join([p for p in [title, main_focus] if p])
    
    # Fetch context for this huddle
    docs = retriever.get_relevant_documents(
        query=retrieval_query,
        provider_filter=None,
        global_filter=None,
    )
    context = retriever.format_context_with_sources(docs)
    
    # Get previous huddle info
    prev_huddle = get_previous_huddle_info(huddles, huddle_id)
    
    # Format huddle prompt
    huddle_details = format_huddle_prompt(
        prompts['huddle_prompt'], plan_result, huddle, prev_huddle,
        min_words, max_words, duration
    )
    
    user_messages = [
        {"role": "user", "content": f"HUDDLE DETAILS (from plan):\n{huddle_details}"},
        {"role": "user", "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}"},
        {"role": "user", "content": "Generate the full Huddle content now."},
    ]
    
    # Generate and return huddle content
    huddle_content = await generate_single_huddle(claude_client, prompts['system_prompt'], user_messages)
    
    return {
        "huddle_id": huddle_id,
        "title": title,
        "content_html": huddle_content,
    }