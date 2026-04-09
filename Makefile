IMG ?= ghcr.io/agentic-layer/presidio:test

.PHONY: all
all: docker-build

.PHONY: docker-build
docker-build:
	docker build -t $(IMG) .

.PHONY: test
test:
	uv run pytest tests/ -v

.PHONY: e2e-test
e2e-test:
	./tests/e2e_test.sh
