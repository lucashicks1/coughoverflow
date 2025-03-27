# Base image
FROM ubuntu:24.04

# Turns off buffering for realtime stdout container logging
ENV PYTHONUNBUFFERED=1
# Turns on noisy segfault logs
ENV PYTHONFAULTHANDLER=1

# Install dependencies
RUN apt-get update && apt-get install -y wget steghide software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.12 && \
    rm -rf /var/lib/apt/lists/*

RUN python3.12 --version

# Get uv
COPY --from=ghcr.io/astral-sh/uv:0.6.4 /uv /uvx /bin/

# Copy project in
ADD . app/

# Sync the project into a new environment, using the frozen lockfile
WORKDIR /app

# Updated computer architecture selection of the OverflowEngine binary.
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
    wget https://github.com/CSSE6400/CoughOverflow-Engine/releases/download/v1.0/overflowengine-amd64 -O overflowengine; \
    else \
    wget https://github.com/CSSE6400/CoughOverflow-Engine/releases/download/v1.0/overflowengine-arm64 -O overflowengine; \
    fi && \
    chmod +x overflowengine


RUN uv sync --frozen

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:$PATH"

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

CMD ["fastapi", "run", "--host", "0.0.0.0", "--port", "8080", "src/cough_overflow/main.py"]
