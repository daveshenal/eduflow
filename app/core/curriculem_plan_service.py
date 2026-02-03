import json
import logging
from pathlib import Path

from config.settings import settings


BASE_DIR = Path(__file__).resolve().parents[2]
PROMPTS_DIR = BASE_DIR / "app" / "prompts"


def _load_json(path: Path) -> dict:
    """Load a JSON file and return its contents as a dict."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fetch_plan_prompts() -> dict:
    """
    Load planning-related prompts from JSON files under app/prompts.

    - system_main.json: contains the shared system prompt as an array of strings
    - curr_plan.json: contains the planner prompt template (array or string)
    """
    system_data = _load_json(PROMPTS_DIR / "system_main.json")
    plan_data = _load_json(PROMPTS_DIR / "curr_plan.json")

    # system_main.json stores system_prompt as an array of strings for readability
    system_raw = system_data.get("system_prompt", [])
    if isinstance(system_raw, list):
        system_prompt = "\n".join(system_raw)
    else:
        system_prompt = str(system_raw) or "You are an assistant that designs simple educational huddle plans."

    planner_raw = plan_data.get(
        "planner_prompt",
        "Create a short curriculum plan for {target_audiance} about {topic}.",
    )
    if isinstance(planner_raw, list):
        planner_prompt = "\n".join(planner_raw)
    else:
        planner_prompt = str(planner_raw)

    return {
        "system_prompt": system_prompt,
        "planner_prompt": planner_prompt,
    }


def get_word_targets(duration: int) -> tuple[int, int]:
    """Get min/max word counts based on duration."""
    duration_to_words = {
        5: (550, 600),
        10: (1200, 1300),
    }

    if duration not in duration_to_words:
        raise ValueError(
            f"Invalid duration: {duration}. Allowed values are {list(duration_to_words.keys())}."
        )

    return duration_to_words[duration]


def format_plan_prompt(prompts: dict, params: dict, min_words: int, max_words: int) -> str:
    """Format the user prompt template with actual values."""
    duration_display = f"{params['duration']} minutes"
    total_duration = f"{params['num_huddles'] * int(params['duration'])} minutes"
    
    try:
        return prompts['planner_prompt'].format(
            target_audiance=params['target_audiance'],
            learning_focus=params['learning_focus'],
            topic=params['topic'],
            clinical_context=params['clinical_context'],
            num_huddles=params['num_huddles'],
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