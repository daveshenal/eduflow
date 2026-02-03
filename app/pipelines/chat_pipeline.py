import json
from pathlib import Path

from app.retrievers.index_data_retriver import PrioritizedRetriever
from config.settings import settings

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_chatbot_prompt() -> str:
    path = _PROMPTS_DIR / "chatbot.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    lines = data.get("chatbot_prompt", [])
    return "\n".join(lines) if isinstance(lines, list) else str(lines)


async def generate_chat_stream(payload: dict, claude_client):
    """Async generator for streaming Chat responses. Uses index_id for retrieval; no user types or AI filters."""

    try:
        index_id: str = payload.get("index_id")

        if not index_id:
            raise ValueError("index_id is required")

        message: str = payload.get("message")
        if not message:
            raise ValueError("message is required")

        retriever = PrioritizedRetriever(
            provider_id=index_id,
            k=settings.INDEX_TOP_K,
            min_score=settings.MIN_SCORE,
        )
        docs = retriever.get_relevant_documents(query=message, filter_expr=None)
        context = retriever.format_context_with_sources(docs)

        user_messages = [
            {"role": "user", "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}"},
            {"role": "user", "content": f"USER QUESTION:\n{message}"},
        ]

        chatbot_prompt = _load_chatbot_prompt()

        async with claude_client.messages.stream(
            model=settings.CLAUDE_MODEL_CHATBOT,
            max_tokens=1024,
            system=chatbot_prompt,
            temperature=0.3,
            messages=user_messages
        ) as stream:
            async for chunk in stream.text_stream:
                yield chunk

            # Get usage info after streaming completes
            final_message = await stream.get_final_message()
            usage = final_message.usage
            print(f"Input tokens: {usage.input_tokens}")
            print(f"Output tokens: {usage.output_tokens}")

    except Exception as e:
        yield f"[ERROR] {e}"