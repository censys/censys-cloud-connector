SHELL:=/usr/bin/env bash

APP_NAME        := censys-cloud-connector
REGISTRY_NAME   := ghcr.io/censys
DOCKER_TAG      := $$(git rev-parse HEAD)
DOCKER_DS       := $$(date -u "+%Y-%m-%d_%H-%M-%S")
DOCKER_IMG      := ${REGISTRY_NAME}/${APP_NAME}:${DOCKER_TAG}

REQUIREMENTS	:= requirements.txt
VENV 			:= .venv
INSTALL_STAMP 	:= ${VENV}/.install.stamp
POETRY 			:= $(shell command -v poetry 2> /dev/null)
EXTRAS 			:= -E azure -E gcp
VERSION			:= $(shell ${POETRY} version -s)

.PHONY: all
all: help

install: $(INSTALL_STAMP)  ## Install the application
$(INSTALL_STAMP): pyproject.toml poetry.lock
	@if [ -z $(POETRY) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	$(POETRY) install $(EXTRAS)
	touch $(INSTALL_STAMP)

.PHONY: clean
clean:
	find . -type d -name "__pycache__" | xargs rm -rf {};
	rm -rf $(INSTALL_STAMP) .coverage .mypy_cache

.PHONY: lock
lock:
	$(POETRY) lock --no-update

.PHONY: requirements
requirements: $(REQUIREMENTS)  ## Builds python requirements.txt
${REQUIREMENTS}: $(INSTALL_STAMP)
	$(POETRY) export -f $(REQUIREMENTS) -o $(REQUIREMENTS) $(EXTRAS) --without-hashes

.PHONY: format
format:
	$(POETRY) run black .
	$(POETRY) run isort .

.PHONY: lint
lint:
	$(POETRY) run flake8 .
	$(POETRY) run mypy -p censys.cloud_connectors

.PHONY: test
test: $(INSTALL_STAMP)  ## Runs tests
	$(POETRY) run pytest --no-cov

.PHONY: test-cov
test-cov: $(INSTALL_STAMP)  ## Runs tests and generates coverage report
	$(POETRY) run pytest --cov --cov-report html

.PHONY: build-image
build-image:  ## Builds docker image
	docker build -t $(DOCKER_IMG) .

.PHONY: push-image
push-image: build-image ## Pushes docker image to gcr
	docker push $(DOCKER_IMG)

# via https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.PHONY: help
help: ## Show make help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
