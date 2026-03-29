import json
import logging
from pathlib import Path

from config.settings import settings
from app.prompts.prompt_management import get_prompt_manager, PromptNames


async def fetch_plan_prompts(db_conn) -> dict:
    """
    Load planning prompts from the prompt manager (DB).
    Uses active prompts: main_prompt (system), curr_planner (planner).
    Returns same shape as fetch_plan_prompts(): system_prompt, planner_prompt.
    """
    manager = get_prompt_manager()
    system_prompt_resp = await manager.get_active_prompt(PromptNames.MAIN_PROMPT.value, db_conn)
    planner_prompt_resp = await manager.get_active_prompt(PromptNames.CURR_PLANNER.value, db_conn)
    if not system_prompt_resp:
        raise ValueError("No active prompt found for 'main_prompt'. Activate a version via /prompts/activate.")
    if not planner_prompt_resp:
        raise ValueError("No active prompt found for 'curr_planner'. Activate a version via /prompts/activate.")
    return {
        "system_prompt": system_prompt_resp.prompt,
        "planner_prompt": planner_prompt_resp.prompt,
    }


def get_word_targets(duration: int) -> tuple[int, int]:
    """Get min/max word counts based on duration."""
    duration_to_words = {
        5: (800, 1000),
        10: (1500, 2000),
    }

    if duration not in duration_to_words:
        raise ValueError(
            f"Invalid duration: {duration}. Allowed values are {list(duration_to_words.keys())}."
        )

    return duration_to_words[duration]


def format_plan_prompt(prompts: dict, params: dict, min_words: int, max_words: int) -> str:
    """Format the user prompt template with actual values."""
    duration_display = f"{params['duration']} minutes"
    total_duration = f"{params['num_docs'] * int(params['duration'])} minutes"
    
    try:
        return prompts['planner_prompt'].format(
            target_audience=params['target_audience'],
            learning_focus=params['learning_focus'],
            topic=params['topic'],
            num_docs=params['num_docs'],
            min_words=min_words,
            max_words=max_words,
            duration_display=duration_display,
            total_duration=total_duration,
        )
    except KeyError as ke:
        error_msg = f"Template formatting error - missing placeholder in planner_prompt: {ke}"
        logging.error(error_msg)
        raise ValueError(error_msg)


async def generate_plan(claude_client, system_prompt: str, user_prompt: str) -> dict:
    """Generate plan using Claude."""
    user_messages = [{"role": "user", "content": user_prompt}]
    
    response = await claude_client.messages.create(
        model=settings.CLAUDE_MODEL_DOC,
        max_tokens=settings.MAX_TOKEN,
        system=system_prompt,
        temperature=0.3,
        messages=user_messages,
    )
    
    logging.info(f"Plan generation - Input tokens: {response.usage.input_tokens}")
    logging.info(f"Plan generation - Output tokens: {response.usage.output_tokens}")
    
    # Join content blocks into a single string
    parts = []
    for block in getattr(response, "content", []) or []:
        if isinstance(block, dict):
            parts.append(block.get("text", ""))
        else:
            parts.append(getattr(block, "text", ""))
    full_text = "".join(parts).strip()
    
    # Parse JSON if possible, else return raw text
    try:
        plan_result = json.loads(full_text)
    except Exception:
        # Try extracting JSON substring
        start = full_text.find("{")
        end = full_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                plan_result = json.loads(full_text[start:end+1])
            except Exception:
                plan_result = {"raw": full_text}
        else:
            plan_result = {"raw": full_text}
    
    # Return both plan result and token usage
    return {
        "plan": plan_result,
        "tokens": {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens
        }
    }