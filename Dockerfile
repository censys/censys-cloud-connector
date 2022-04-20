ARG PYTHON_VERSION=3.9

FROM python:${PYTHON_VERSION}-slim

LABEL org.opencontainers.image.title="Censys Cloud Connector" \
      org.opencontainers.image.description="The Censys Unified Cloud Connector is a standalone connector that gathers assets from various cloud providers and stores them in Censys ASM." \
      org.opencontainers.image.authors="Censys, Inc." \
      org.opencontainers.image.license="Apache-2.0" \
      org.opencontainers.image.source=https://github.com/censys/censys-cloud-connector \
      org.opencontainers.image.documentation=https://github.com/censys/censys-cloud-connector#readme \
      org.opencontainers.image.base.name="registry.hub.docker.com/library/python:${PYTHON_VERSION}-slim"

# Default extras to support both Azure and GCP
ARG EXTRAS="azure gcp"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.1.13 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

COPY src/ /app/src/
COPY pyproject.toml poetry.lock /app/

RUN pip3 install --upgrade pip "poetry==$POETRY_VERSION"
RUN poetry install --no-dev --extras "${EXTRAS}"

CMD ["scan"]
ENTRYPOINT ["censys-cc"]
