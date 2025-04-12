# Base image
FROM ubuntu:24.04


# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \ 
    PYTHONFAULTHANDLER=1 \
    UV_CACHE_DIR=/root/.cache/uv \
    PATH="/root/.local/bin:$PATH"


# Install cough overflow dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    steghide \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Updated computer architecture selection of the OverflowEngine binary.
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
    wget https://github.com/CSSE6400/CoughOverflow-Engine/releases/download/v1.0/overflowengine-amd64 -O overflowengine; \
    else \
    wget https://github.com/CSSE6400/CoughOverflow-Engine/releases/download/v1.0/overflowengine-arm64 -O overflowengine; \
    fi && \
    chmod +x overflowengine

# Download installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run and remove installer
RUN sh /uv-installer.sh && rm /uv-installer.sh

RUN uv venv --python 3.12.0 .venv

# Sync the project into a new environment
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

CMD ["uv", "run", "fastapi", "run", "--host", "0.0.0.0", "--port", "8080", "src/cough_overflow/main.py"]
