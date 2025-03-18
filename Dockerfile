# Base image
FROM python:3.12-bullseye

# Turns off buffering for realtime stdout container logging
ENV PYTHONUNBUFFERED=1
# Turns on noisy segfault logs
ENV PYTHONFAULTHANDLER=1

# Get uv in (Not sure if I like having this bloat though?)
COPY --from=ghcr.io/astral-sh/uv:0.6.4 /uv /uvx /bin/

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

WORKDIR /app/

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Install overflow engine deps.
RUN apt-get update && apt-get install -y wget steghide && rm -rf /var/lib/apt/lists/*

# Get the overflow engine
RUN dpkg --print-architecture | grep -q "amd64" && export ARCH="amd64" || export ARCH="arm64" && wget https://github.com/CSSE6400/CoughOverflow-Engine/releases/download/v1.0/overflowengine-${ARCH} -O overflowengine && chmod +x overflowengine


CMD ["fastapi", "run", "--host", "0.0.0.0", "--port", "8080", "src/cough_overflow/main.py"]
