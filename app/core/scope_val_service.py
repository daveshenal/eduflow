"""
Script for Scope validation
"""

from config.settings import settings
from app.prompts.prompt_management import get_db_connection, get_manager


# Domain validation function
async def scope_validation(payload: dict, claude_client):
    try:
        message = "\n".join([  # Prepare the structured message for Claude input
            f"Topic: {payload.get('topic')}",                  
            f"Clinical Context: {payload.get('clinicalContext')}",
            f"Learning Focus: {payload.get('learningFocus')}",
            f"Role: {payload.get('role')}",
            f"Discipline: {payload.get('discipline')}",
        ])

        # Construct the user message for Claude model
        user_messages = [
            {"role": "user", "content": f"USER INPUTS (Home Health Only):\n{message}"}
        ]
        
        async with get_db_connection() as db_conn:
            prompt_manager = get_manager("use_case_prompts")
            obj = await prompt_manager.get_active_prompt("scope_validation", db_conn)
            scope_prompt = obj.prompt
        
        # Send the request to Claude
        response = await claude_client.messages.create(
            model=settings.CLAUDE_MODEL_HUDDLE,
            system=scope_prompt,
            messages=user_messages,
            max_tokens=512,
            temperature=0.1
        )

        # Access the response content for the structured output
        structured_response = response.content[0].text

        # Parse the structured response assuming Claude returns it as a JSON-like string (dictionary)
        # If the output is not in the right format, handle it accordingly
        try:
            parsed_response = eval(structured_response)  # Convert the response to a dictionary
            yield parsed_response
        except Exception as e:
            yield {
                "validity": "invalid",
                "user_message": "Unable to process the response.",
                "explanation": f"Error processing Claude's response: {e}"
            }

    except Exception as e:
        yield {
            "validity": "invalid",
            "user_message": "An error occurred during the scope validation process.",
            "explanation": str(e)
        }