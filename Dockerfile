FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set the working directory
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

# Copy lock and project configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (without installing the project itself yet)
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application code
COPY . .

# Sync the project
RUN uv sync --frozen --no-dev

# Expose default port for FastMCP SSE transport
EXPOSE 8000

# Run the entry point
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "main.py"]
