import logging
import json

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
                        prev_huddle: dict, min_words: int, max_words: int, duration: int,
                        huddle_id: int, total_huddles: int, agency_name: str = None, branch_name: str = None) -> str:
    """Format huddle generation prompt."""
    try:
        # Determine if this is first or last huddle
        is_first_or_last = huddle_id == 1 or huddle_id == total_huddles
        
        # Convert dict to JSON string for template formatting
        if is_first_or_last:
            complete_curriculum = json.dumps(plan_result, indent=2)
        else:
            complete_curriculum = "N/A"
        
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
            previous_key_concepts=prev_huddle['key_concepts'],
            complete_curriculum=complete_curriculum,
            agency_name=agency_name or "N/A",
            branch_name=branch_name or "N/A"
        )
    except KeyError as ke:
        error_msg = f"Template formatting error - missing placeholder in huddle prompt: {ke}"
        logging.error(error_msg)
        raise ValueError(error_msg)


async def generate_single_huddle(claude_client, system_prompt: str, user_messages: list) -> dict:
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


async def process_single_huddle(claude_client, huddle: dict, huddle_id: int, plan_result: dict, 
                               huddles: list, retriever, prompts: dict, min_words: int, max_words: int,
                               duration: int, global_filter: str = None, agency_name: str = None, branch_name: str = None):
    """
    Generate and return the HTML content for a single huddle.
    """
    title = huddle.get("title")
    main_focus = huddle.get("main_focus")
    retrieval_query = huddle.get("retrieval_query") + " " + " ".join([p for p in [title, main_focus] if p])
    
    # Fetch context for this huddle
    docs = retriever.get_relevant_documents(
        query=retrieval_query,
        provider_filter=None,
        global_filter=global_filter,
    )
    context = retriever.format_context_with_sources(docs)
    
    # Get previous huddle info
    prev_huddle = get_previous_huddle_info(huddles, huddle_id)
    
    # Format huddle prompt
    huddle_details = format_huddle_prompt(
        prompts['huddle_prompt'], plan_result, huddle, prev_huddle,
        min_words, max_words, duration, huddle_id, len(huddles),
        agency_name, branch_name
    )
    
    user_messages = [
        {"role": "user", "content": f"HUDDLE DETAILS (from plan):\n{huddle_details}"},
        {"role": "user", "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}"},
        {"role": "user", "content": "Generate the full Huddle content now."},
    ]
    
    # Generate and return huddle content
    huddle_result = await generate_single_huddle(claude_client, prompts['system_prompt'], user_messages)
    
    return {
        "huddle_id": huddle_id,
        "title": title,
        "content_html": huddle_result["content"],
        "tokens": huddle_result["tokens"]
    }