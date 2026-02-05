from anthropic import AsyncAnthropic
from config.settings import settings

def get_claude_client():
    claude_client = AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
    return claude_client