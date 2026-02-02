from config.settings import settings
from app.prompts.prompt_management import get_manager, get_db_connection

async def fetch_voicescript_prompts() -> dict:
    """Fetch voice script prompt from database."""
    async with get_db_connection() as db_conn:
        manager = get_manager("use_case_prompts")
        obj = await manager.get_active_prompt("voice_script", db_conn)
        
        if not obj or not obj.prompt.strip():
            error_msg = "Required voice_script prompt not found in database"
            raise ValueError(error_msg)
        
        return {"voice_script_prompt": obj.prompt}

async def generate_voiceover_script(payload: dict, claude_client) -> dict:
    """Convert a generated Huddle (HTML) into a narration-ready voiceover script.

    Expected payload keys:
    - huddleHtml | huddle | content: The Huddle HTML to transform
    - tone (optional): stylistic guidance, e.g., "professional, warm, clear"
    - paceWpm (optional): target speaking pace in words per minute (default ~155)
    """
    huddle_html: str = (payload.get("huddleHtml"))
    if not huddle_html or not huddle_html.strip():
        raise ValueError("huddleHtml is required")

    tone: str = payload.get("tone") or "professional, warm, clear"
    pace_wpm = payload.get("paceWpm") or 140
    duration = payload.get("duration")

    # Fetch prompt from database
    prompts = await fetch_voicescript_prompts()
    
    # Format the system prompt with parameters
    system_prompt = prompts['voice_script_prompt'].format(
        tone=tone,
        pace_wpm=pace_wpm,
        duration=f"{duration} minutes",
    )

    user_messages = [
        {
            "role": "user",
            "content": (
                "OBJECTIVE:\nTransform the provided Huddle HTML into a narration-only voiceover script following the rules."
            ),
        },
        {
            "role": "user",
            "content": f"HUDDLE_HTML:\n{huddle_html}",
        },
        {
            "role": "user",
            "content": "Return only the final script as plain text.",
        },
    ]

    try:
        response = await claude_client.messages.create(
            model=settings.CLAUDE_MODEL_HUDDLE,
            max_tokens=settings.MAX_TOKEN,
            system=system_prompt,
            temperature=0.3,
            messages=user_messages,
        )

        print(f"Input tokens: {response.usage.input_tokens}")
        print(f"Output tokens: {response.usage.output_tokens}")

        # Join content blocks into a single string (supports SDK dict or object forms)
        parts = []
        for block in getattr(response, "content", []) or []:
            if isinstance(block, dict):
                parts.append(block.get("text", ""))
            else:
                parts.append(getattr(block, "text", ""))
        script = "".join(parts).strip()
        
        # Return both script and token usage
        return {
            "script": script,
            "tokens": {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens
            }
        }
    except Exception as e:
        # Re-raise for the API layer to return as HTTP error
        raise e