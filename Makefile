.PHONY: help up down ollama-up ollama-logs test test-local test-local-up test-unit

ANALYST_MODEL ?= analyst-local-fast
PY ?= python3

help:
	@echo "Targets:"
	@echo "  up            - levanta todo el stack (docker compose up --build)"
	@echo "  down          - detiene el stack"
	@echo "  ollama-up     - levanta solo ollama + ollama-init y espera a que los modelos esten listos"
	@echo "  ollama-logs   - logs de ollama / ollama-init"
	@echo "  test          - pytest completo (integration/agent skip sin infra)"
	@echo "  test-unit     - solo unitarios (sin Docker)"
	@echo "  test-local    - pytest con modelo local (requiere DB levantada + ollama-up)"
	@echo "  test-local-up - levanta ollama + DBs, corre pytest con modelo local, baja al finish"

up:
	docker compose up --build

down:
	docker compose down

ollama-up:
	docker compose up -d ollama
	@echo ">> esperando a que ollama-init descargue los modelos..."
	docker compose up ollama-init
	@echo ">> modelos listos"

ollama-logs:
	docker compose logs -f ollama ollama-init

test:
	$(PY) -m pytest tests -q

test-unit:
	$(PY) -m pytest tests/unit -q

test-local:
	ANALYST_MODEL=$(ANALYST_MODEL) RUN_AGENT=1 $(PY) -m pytest tests -q

test-local-up: ollama-up
	docker compose up -d postgres analytics redis
	@echo ">> esperando DBs..."
	@sleep 5
	-ANALYST_MODEL=$(ANALYST_MODEL) RUN_AGENT=1 $(PY) -m pytest tests -q
	@echo ">> bajando stack temporal..."
	docker compose down