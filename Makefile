IMG ?= ghcr.io/agentic-layer/presidio:test

.PHONY: all
all: docker-build

.PHONY: docker-build
docker-build:
	docker build -t $(IMG) .

.PHONY: e2e-test
e2e-test:
	./tests/e2e_test.sh $(IMG)
