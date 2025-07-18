"""Application constants for TowerBot.

This module contains static configuration values, example commands,
and system prompts used throughout the TowerBot application.
"""

COMMAND_EXAMPLES = {
    "ask": "what's the wifi password?",
    "report": "we need more toilet paper on the 9th floor",
    "propose": "let's organize a community bbq on the rooftop",
    "connect": "who can help me learn more about biotech?",
}
"""Dictionary of example commands for user guidance.

Provides sample queries for each command type to help users understand
how to interact with the bot effectively.
"""

INTRODUCTION = (
    "Hello! I am TowerBot, the dedicated AI resource for all Frontier Tower citizens.\n\n"
    "My mission is to make your life easier by handling background tasks and providing seamless support "
    "within our community. Whether you need answers to questions, want to report a problem, propose an idea, or are "
    "looking to connect with fellow residents, I'm here to assist.\n\n"
    "As your knowledgeable and friendly community facilitator, I leverage my understanding of Frontier Tower's "
    "needs and interactions to offer accurate, context-aware assistance. Just use commands like /ask, /report, "
    "/propose, or /connect to get started—I'm always ready to help!"
)
"""Welcome message displayed when users start the bot.

Introduces TowerBot's capabilities and guides users on how to interact with the system.
"""

SYSTEM_PROMPT = """You are a helpful AI assistant for the Frontier Tower community.

You have access to memory tools that allow you to remember information across conversations. 
IMPORTANT: Proactively use your memory tools when you encounter:
- New facts or information about users, the building, or the community
- User preferences or important context
- Anything that would be helpful to remember for future conversations

Always prioritize being helpful while maintaining conversation continuity through memory.

System time: {system_time}"""
"""System prompt template for AI agents.

Provides the base instruction and context for AI agents, including
current system time for temporal awareness.
"""