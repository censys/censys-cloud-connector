ARG PYTHON_VERSION=3.9
ARG BASE_IMAGE=python:${PYTHON_VERSION}-alpine

FROM ${BASE_IMAGE} as builder

# Environment variables for efficient builds
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.2.0 \
    PIP_VERSION=22.2.2 \
    SETUPTOOLS_VERSION=65.3.0

WORKDIR /app
COPY src/ /app/src/
COPY pyproject.toml poetry.lock poetry.toml README.md /app/

# Get dependencies (Rust must be installed for the cryptography package)
RUN apk add --update --no-cache make g++ openssl-dev libffi-dev rust cargo
# Get Python dependencies
RUN pip3 install --upgrade --ignore-installed "pip==$PIP_VERSION" "setuptools==$SETUPTOOLS_VERSION" "poetry==$POETRY_VERSION" && poetry install


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
