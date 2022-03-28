SHELL:=/usr/bin/env bash

APP_NAME        := cloud-connector
REGISTRY_NAME   := gcr.io/censys-io
DOCKER_TAG      := $$(git rev-parse HEAD)
DOCKER_DS       := $$(date -u "+%Y-%m-%d_%H-%M-%S")
DOCKER_IMG      := ${REGISTRY_NAME}/${APP_NAME}:${DOCKER_TAG}


.PHONY: all
all: help

.PHONY: build-image
build-image:  ## Builds docker image
	docker build -t ${DOCKER_IMG} .

.PHONY: push-image
push-image: build-image ## pushes docker image to gcr
	docker push ${DOCKER_IMG}

# via https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.PHONY: help
help: ## Show make help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
