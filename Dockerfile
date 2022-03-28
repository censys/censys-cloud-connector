ARG PYTHON_VERSION=3.9

FROM python:${PYTHON_VERSION}-slim

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
