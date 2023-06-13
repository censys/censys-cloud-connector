ARG PYTHON_VERSION=3.9
ARG BASE_IMAGE=python:${PYTHON_VERSION}-alpine

# Target with build dependencies
FROM ${BASE_IMAGE} as builder

# Environment variables for efficient builds
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.4.0 \
    PIP_VERSION=23.0.1 \
    SETUPTOOLS_VERSION=67.4.0

# Set the working directory
WORKDIR /app

# Copy the source code
COPY src/ /app/src/

# Copy the configuration/dependency files
COPY pyproject.toml poetry.lock poetry.toml README.md /app/

# Install OS dependencies (Rust must be installed for the cryptography package)
RUN apk add --update --no-cache make g++ openssl-dev libffi-dev rust cargo

# Install Python dependencies
RUN pip3 install --upgrade --ignore-installed "pip==$PIP_VERSION" "setuptools==$SETUPTOOLS_VERSION" "poetry==$POETRY_VERSION" && poetry install --without dev


# Target with dev dependencies
FROM builder as dev

# Install Python dev dependencies
RUN poetry install --with dev


# Target with tests
FROM dev as test

# Copy the tests
COPY tests/ /app/tests/

# Run the tests
RUN poetry run pytest


# Target with linting
FROM dev as lint

# Run the tests
RUN poetry run black --check .
RUN poetry run isort --check .
RUN poetry run flake8 .
RUN poetry run mypy -p censys.cloud_connectors


# Target for the final image
FROM ${BASE_IMAGE} as app

# Set labels
LABEL org.opencontainers.image.title="Censys Cloud Connector" \
    org.opencontainers.image.description="The Censys Unified Cloud Connector is a standalone connector that gathers assets from various cloud providers and stores them in Censys ASM." \
    org.opencontainers.image.authors="Censys, Inc. <support@censys.io>" \
    org.opencontainers.image.licenses="Apache-2.0" \
    org.opencontainers.image.source=https://github.com/censys/censys-cloud-connector \
    org.opencontainers.image.documentation=https://github.com/censys/censys-cloud-connector#readme \
    org.opencontainers.image.base.name="registry.hub.docker.com/library/${BASE_IMAGE}"

# Install OS dependencies and create a non-root user
RUN apk add --update --no-cache libstdc++ && \
    addgroup -g 1000 censys && \
    adduser -D -h /app -s /bin/bash -G censys -u 1000 censys

# Set the user and working directory
USER censys
WORKDIR /app

# Copy the source code
COPY --from=builder --chown=censys /app ./

# Set the command
CMD ["/app/.venv/bin/censys-cc", "scan"]
