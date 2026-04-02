"""Chat pipeline for streaming responses using Claude."""

from app.adapters.azure_sql import get_db_connection
from app.prompts.prompt_management import get_prompt_manager
from app.retrievers.index_data_retriver import PrioritizedRetriever
from config.settings import settings


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
            index_id=index_id,
            k=settings.INDEX_TOP_K,
            min_score=settings.MIN_SCORE,
        )
        docs = retriever.get_relevant_documents(
            query=message, filter_expr=None)
        context = retriever.format_context_with_sources(docs)

        user_messages = [
            {"role": "user", "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}"},
            {"role": "user", "content": f"USER QUESTION:\n{message}"},
        ]

        async with get_db_connection() as db_conn:
            prompt_manager = get_prompt_manager()
            obj = await prompt_manager.get_active_prompt("developer_chatbot", db_conn)
            if obj is None:
                raise ValueError(
                    "No active prompt found for 'developer_chatbot'")
            chatbot_prompt = obj.prompt

        async with claude_client.messages.stream(
            model=settings.CLAUDE_MODEL_CHATBOT,
            max_tokens=1024,
            system=chatbot_prompt,
            cache_control={"type": "ephemeral"},
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
