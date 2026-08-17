.PHONY: help up down ollama-up ollama-logs test test-local test-local-up test-unit \
       image-build image-push image deploy-cce chatbot-up chatbot-logs

ANALYST_MODEL ?= analyst-local-fast
PY ?= python3

# ---- Imagen Docker para SWR (Huawei Cloud) ----
# Configurar via env o deploy/cce/.env:
#   SWR_REGION=cn-north-4
#   SWR_ORG=mi-org
#   IMAGE_TAG=latest
SWR_REGION ?= cn-north-4
SWR_ORG    ?= mi-org
IMAGE_TAG  ?= latest
IMAGE      := swr.$(SWR_REGION).myhuaweicloud.com/$(SWR_ORG)/analyst-api:$(IMAGE_TAG)

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
	@echo "  chatbot-up    - levanta solo el chatbot Chainlit (requiere API corriendo)"
	@echo "  chatbot-logs  - logs del chatbot"
	@echo ""
	@echo "Imagen Docker (SWR Huawei Cloud):"
	@echo "  image-build   - construye la imagen (IMAGE=$(IMAGE))"
	@echo "  image-push    - hace login en SWR y push de la imagen"
	@echo "  image         - image-build + image-push"
	@echo ""
	@echo "Deploy CCE:"
	@echo "  deploy-cce    - aplica manifests de deploy/cce/ en orden"

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

# ---- Chatbot (Chainlit) ----

chatbot-up:
	docker compose up -d chatbot
	@echo ">> chatbot en http://localhost:8001"

chatbot-logs:
	docker compose logs -f chatbot

# ---- Imagen Docker ----

image-build:
	@echo ">> construyendo $(IMAGE)"
	docker build -t $(IMAGE) .

image-push:
	@echo ">> login en SWR $(SWR_REGION)..."
	@docker login -u $(SWR_ORG) -p $$(echo $$SWR_PASSWORD) swr.$(SWR_REGION).myhuaweicloud.com 2>/dev/null || \
		{ echo "!! set SWR_PASSWORD env var (token de SWR)"; exit 1; }
	@echo ">> push $(IMAGE)"
	docker push $(IMAGE)

image: image-build image-push
	@echo ">> imagen publicada: $(IMAGE)"

# ---- Deploy CCE ----

deploy-cce:
	@echo ">> creando ConfigMap de SQL analytics..."
	sh deploy/cce/create-configmaps.sh
	@echo ">> aplicando manifests..."
	kubectl apply -f deploy/cce/00-namespace.yaml
	kubectl apply -f deploy/cce/01-secrets.yaml
	kubectl apply -f deploy/cce/02-configmaps.yaml
	kubectl apply -f deploy/cce/03-pvcs.yaml
	kubectl apply -f deploy/cce/10-postgres-agent.yaml
	kubectl apply -f deploy/cce/11-postgres-analytics.yaml
	kubectl apply -f deploy/cce/12-redis.yaml
	kubectl apply -f deploy/cce/13-ollama.yaml
	@echo ">> esperando a que ollama este listo..."
	kubectl rollout status deployment/ollama -n data-analyst-agent --timeout=120s
	@echo ">> aplicando job de init de ollama..."
	kubectl apply -f deploy/cce/14-ollama-init-job.yaml
	kubectl wait job/ollama-init -n data-analyst-agent --for=condition=complete --timeout=600s
	@echo ">> aplicando litellm y api..."
	kubectl apply -f deploy/cce/15-litellm.yaml
	kubectl apply -f deploy/cce/16-api.yaml
	kubectl apply -f deploy/cce/17-elb.yaml
	@echo ">> deploy aplicado. EIP del ELB:"
	kubectl get svc api-elb -n data-analyst-agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "(pendiente)"