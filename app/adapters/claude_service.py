from anthropic import AsyncAnthropic
from config.settings import settings

claude_client = AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)

def get_claude_client():
    return claude_client