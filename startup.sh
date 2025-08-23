# 1. Generate enums (runs once and finishes)
uv run python scripts/generate_enums.py

# 2. Start the webhook process in the background
uv run python -m app.webhook &

# 3. Start the main web server in the foreground
uv run uvicorn app.main:app --reload --port 8000 --host 0.0.0.0