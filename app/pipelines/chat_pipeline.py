from app.retrievers.index_data_retriver import PrioritizedRetriever
from config.settings import settings

async def generate_chat_stream(payload: dict, claude_client):
    """Async generator for streaming Chat responses"""

    try:
        provider_id: str = payload.get("providerId")
        if not provider_id:
            raise ValueError("provider_id is required")

        user_type: str = payload.get("userType")
        message: str = payload.get("message")

        context = ""

        if user_type != "developer":
            retriever = PrioritizedRetriever(
                provider_id=provider_id,
                k=settings.INDEX_TOP_K,
                min_score=settings.MIN_SCORE,
            )
            ai_filter = retriever.build_ai_filter(
                branch_state=payload.get('branchState'),
                certifications=payload.get('certificationList'),
            )
            docs = retriever.get_relevant_documents(
                query=message,
                filter_expr=ai_filter,
            )

            context = retriever.format_context_with_sources(docs)

        user_messages = [
            {"role": "user", "content": f"CONTEXT FROM KNOWLEDGEBASE:\n{context}"},
            {"role": "user", "content": f"USER QUESTION:\n{message}"}
        ]
        
        async with get_db_connection() as db_conn:
            prompt_manager = get_manager("use_case_prompts")
            obj = await prompt_manager.get_active_prompt("developer_chatbot", db_conn)
            chatbot_prompt = obj.prompt

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