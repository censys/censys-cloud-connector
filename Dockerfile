ARG PYTHON_VERSION=3.9
ARG BASE_IMAGE=python:${PYTHON_VERSION}-alpine

FROM ${BASE_IMAGE} as builder

# Default extras to support all cloud providers
ARG EXTRAS="aws azure gcp"

# Environment variables for efficient builds
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.1.13 \
    POETRY_NO_INTERACTION=1

WORKDIR /app
COPY src/ /app/src/
COPY pyproject.toml poetry.lock poetry.toml README.md /app/

# Get dependencies (Rust must be installed for the cryptography package)
RUN apk add --update --no-cache make g++ openssl-dev libffi-dev rust cargo && \
                                pip3 install --upgrade pip setuptools "poetry==$POETRY_VERSION" && \
                                poetry install --no-dev --extras "${EXTRAS}"


FROM ${BASE_IMAGE} as app

LABEL org.opencontainers.image.title="Censys Cloud Connector" \
      org.opencontainers.image.description="The Censys Unified Cloud Connector is a standalone connector that gathers assets from various cloud providers and stores them in Censys ASM." \
      org.opencontainers.image.authors="Censys, Inc. <support@censys.io>" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source=https://github.com/censys/censys-cloud-connector \
      org.opencontainers.image.documentation=https://github.com/censys/censys-cloud-connector#readme \
      org.opencontainers.image.base.name="registry.hub.docker.com/library/${BASE_IMAGE}"

RUN apk add --update --no-cache libstdc++ && \
    addgroup -g 1000 censys && \
    adduser -D -h /app -s /bin/bash -G censys -u 1000 censys
USER censys
WORKDIR /app
COPY --from=builder --chown=censys /app ./

CMD ["scan"]
ENTRYPOINT ["/app/.venv/bin/censys-cc"]
