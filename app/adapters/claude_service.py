"""Factory for the async Anthropic (Claude) API client."""

from anthropic import AsyncAnthropic
from config.settings import settings


def get_claude_client():
    """Build and return an AsyncAnthropic client using app settings."""
    claude_client = AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
    return claude_client
