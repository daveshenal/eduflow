import json
import logging

from config.settings import settings
from app.prompts.prompt_management import get_manager, get_db_connection


def get_word_targets(duration: int) -> tuple[int, int]:
    """Get min/max word counts based on duration."""
    duration_to_words = {
        5: (550, 600),
        10: (1100, 1250),
    }

    if duration not in duration_to_words:
        raise ValueError(
            f"Invalid duration: {duration}. Allowed values are {list(duration_to_words.keys())}."
        )

    return duration_to_words[duration]


async def fetch_plan_prompts(role_value: str, discipline_value: str) -> dict:
    """Fetch all prompts needed for plan generation."""
    async with get_db_connection() as db_conn:
        prompts_to_fetch = [
            ("main_prompts", "main_prompt", "system_prompt"),
            ("use_case_prompts", "huddle_planner", "planner_prompt"),
            ("role_prompts", role_value, "role_prompt"),
            ("discipline_prompts", discipline_value, "discipline_prompt")
        ]
        
        prompt_vars = {}
        for manager_name, key, var_name in prompts_to_fetch:
            manager = get_manager(manager_name)
            obj = await manager.get_active_prompt(key, db_conn)
            prompt_vars[var_name] = obj.prompt if obj else ""
    
    # Validate all required prompts are present
    missing_prompts = []
    for key, value in prompt_vars.items():
        if not value or not value.strip():
            missing_prompts.append(key)
    
    if missing_prompts:
        error_msg = f"Required prompts not found in database: {', '.join(missing_prompts)}"
        logging.error(error_msg)
        raise ValueError(error_msg)
    
    return prompt_vars


def format_plan_prompt(prompts: dict, params: dict, action_plan: str, min_words: int, max_words: int) -> str:
    """Format the user prompt template with actual values."""
    duration_display = f"{params['duration']} minutes"
    total_duration = f"{params['num_huddles'] * int(params['duration'])} minutes"
    
    try:
        return prompts['planner_prompt'].format(
            role_prompt=prompts['role_prompt'],
            discipline_prompt=prompts['discipline_prompt'],
            learning_focus=params['learning_focus'],
            topic=params['topic'],
            expected_outcomes="Not Provided",
            clinical_context=params['clinical_context'],
            action_plan=action_plan,
            num_huddles=params['num_huddles'],
            min_words=min_words,
            max_words=max_words,
            duration_display=duration_display,
            role_label=params['role_label'],
            discipline_label=params['discipline_label'],
            total_duration=total_duration,
            role_value=params['role_value'],
            discipline_value=params['discipline_value'],
            provider_id=params['provider_id']
        )
    except KeyError as ke:
        error_msg = f"Template formatting error - missing placeholder in planner_prompt: {ke}"
        logging.error(error_msg)
        raise ValueError(error_msg)


async def generate_plan(claude_client, system_prompt: str, user_prompt: str) -> dict:
    """Generate huddle plan using Claude."""
    user_messages = [{"role": "user", "content": user_prompt}]
    
    response = await claude_client.messages.create(
        model=settings.CLAUDE_MODEL_HUDDLE,
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
        return json.loads(full_text)
    except Exception:
        # Try extracting JSON substring
        start = full_text.find("{")
        end = full_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(full_text[start:end+1])
            except Exception:
                return {"raw": full_text}
        else:
            return {"raw": full_text}