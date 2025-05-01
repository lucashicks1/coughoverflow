# Get engine
FROM ubuntu:24.04 AS engine

# Install cough overflow dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download binary 
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
    wget https://github.com/CSSE6400/CoughOverflow-Engine/releases/download/v1.0/overflowengine-amd64 -O overflowengine; \
    else \
    wget https://github.com/CSSE6400/CoughOverflow-Engine/releases/download/v1.0/overflowengine-arm64 -O overflowengine; \
    fi && \
    chmod +x overflowengine

# Build stage
FROM golang:1.24-alpine AS build

# Set the working directory
WORKDIR /app

# Copy and download dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy the source code
COPY . .

# Build the Go application
RUN CGO_ENABLED=0 GOOS=linux go build

# Final stage
FROM ubuntu:24.04

# Copy overflowengine
COPY --from=engine /overflowengine .

RUN apt-get update && apt-get install -y --no-install-recommends \
    steghide \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy the binary from the build stage
COPY --from=build /app/worker .

# Set the entrypoint command
ENTRYPOINT ["/worker"]
