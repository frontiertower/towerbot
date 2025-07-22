FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Generate enums from ontology during build
RUN /app/.venv/bin/python scripts/generate_enums.py

# Run the webhook setup script first, then start the Uvicorn server.
CMD /app/.venv/bin/python -m app.webhook \
    && /app/.venv/bin/uvicorn app.main:app --workers 1 --host 0.0.0.0 --port 3000