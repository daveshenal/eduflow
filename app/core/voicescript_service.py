from config.settings import settings
from app.prompts.prompt_management import get_prompt_manager, PromptNames
from app.adapters.azure_sql import get_db_connection

async def fetch_voicescript_prompts(db_conn) -> dict:
    """Fetch voice script prompt from database."""
    manager = get_prompt_manager()
    voice_prompt_resp = await manager.get_active_prompt(PromptNames.VOICESCRIPT.value, db_conn)

    if not voice_prompt_resp:
        raise ValueError(
            "No active prompt found for 'voice_script'. Activate a version via /prompts/activate.")

    return {"voice_script_prompt": voice_prompt_resp.prompt}

async def generate_voiceover_script(payload: dict, claude_client) -> dict:
    """Convert a generated content (HTML) into a narration-ready voiceover script.

    Expected payload keys:
    - contentHtml: The content HTML to transform
    - tone (optional): stylistic guidance, e.g., "professional, warm, clear"
    - paceWpm (optional): target speaking pace in words per minute (default ~140)
    """
    content_html: str = (payload.get("contentHtml"))
    if not content_html or not content_html.strip():
        raise ValueError("contentHtml is required")

    tone: str = payload.get("tone") or "professional, warm, clear"
    pace_wpm = payload.get("paceWpm") or 140
    duration = payload.get("duration")

    # Fetch prompt from database
    async with get_db_connection() as db_conn:
        prompts = await fetch_voicescript_prompts(db_conn)

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
                "OBJECTIVE:\nTransform the provided content HTML into a narration-only voiceover script following the rules."
            ),
        },
        {
            "role": "user",
            "content": f"content_HTML:\n{content_html}",
        },
        {
            "role": "user",
            "content": "Return only the final script as plain text.",
        },
    ]

    try:
        response = await claude_client.messages.create(
            model=settings.CLAUDE_MODEL_DOC,
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
