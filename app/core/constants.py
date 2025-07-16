
COMMAND_EXAMPLES = {
    "ask": "what's the wifi password?",
    "help": "we need more toilet paper on the 9th floor",
    "connect": "who can help me learn more about biotech?",
}

INTRODUCTION = (
    "Hello! I am TowerBot, the dedicated AI resource for all Frontier Tower citizens.\n\n"
    "My mission is to make your life easier by handling background tasks and providing seamless support "
    "within our community. Whether you need answers to questions, want to submit a help ticket, or are "
    "looking to connect with fellow residents, I'm here to assist.\n\n"
    "As your knowledgeable and friendly community facilitator, I leverage my understanding of Frontier Tower's "
    "needs and interactions to offer accurate, context-aware assistance. Just use commands like /ask, /help, "
    "or /connect to get started—I'm always ready to help!"
)

SYSTEM_PROMPT = """You are a helpful AI assistant.

System time: {system_time}"""