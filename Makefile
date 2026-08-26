.PHONY: help up down ollama-up ollama-logs test test-local test-local-up test-unit \
       image-build image-push image mirror-images deploy deploy-cce chatbot-up chatbot-logs \
       mcp-up mcp-logs tf-init tf-plan tf-apply tf-destroy \
       clean clean-docker clean-images clean-tf clean-all

ANALYST_MODEL ?= analyst-local-fast
PY ?= python3

# ---- Imagen Docker para SWR (Huawei Cloud) ----
# Configurar via env:
#   HW_ACCESS_KEY / HW_SECRET_KEY  (para login AK/SK)
#   SWR_REGION=la-north-2
#   SWR_ORG=langchain-test
#   IMAGE_TAG=latest
SWR_REGION ?= la-north-2
SWR_ORG    ?= langchain-test
IMAGE_TAG  ?= latest
TF_BUCKET  ?= cce-litellm
SWR_HOST   := swr.$(SWR_REGION).myhuaweicloud.com
IMAGE           := $(SWR_HOST)/$(SWR_ORG)/analyst-api:$(IMAGE_TAG)
CHATBOT_IMAGE   := $(SWR_HOST)/$(SWR_ORG)/analyst-chatbot:$(IMAGE_TAG)

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
	@echo "  mcp-up        - levanta los servidores MCP (glossary + explorer)"
	@echo "  mcp-logs      - logs de los servidores MCP"
	@echo ""
	@echo "Imagen Docker (SWR Huawei Cloud):"
	@echo "  image-build   - construye API + Chatbot (IMAGE=$(IMAGE))"
	@echo "  image-push    - login en SWR (AK/SK) + push de API + Chatbot"
	@echo "  image         - image-build + image-push"
	@echo "  mirror-images - hace mirror de postgres/redis/ollama/litellm a SWR"
	@echo ""
	@echo "Deploy CCE:"
	@echo "  deploy        - build + push + mirror + terraform apply (end-to-end)"
	@echo "  deploy-cce    - (legacy) aplica manifests deploy/cce/ con kubectl"
	@echo ""
	@echo "Terraform (Huawei Cloud CCE):"
	@echo "  tf-init       - terraform init"
	@echo "  tf-plan       - terraform plan"
	@echo "  tf-apply      - terraform apply"
	@echo "  tf-destroy    - terraform destroy"
	@echo ""
	@echo "Limpieza:"
	@echo "  clean         - detiene contenedores y elimina volúmenes Docker"
	@echo "  clean-images  - elimina imágenes Docker del proyecto"
	@echo "  clean-tf      - elimina recursos Terraform (Huawei Cloud)"
	@echo "  clean-all     - limpia Docker + Terraform + archivos temporales"

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

# ---- Servidores MCP ----

mcp-up:
	docker compose up -d mcp-glossary mcp-explorer
	@echo ">> MCP glossary en http://localhost:8100/mcp"
	@echo ">> MCP explorer en http://localhost:8101/mcp"

mcp-logs:
	docker compose logs -f mcp-glossary mcp-explorer

# ---- Imagen Docker ----

# Login a SWR con AK/SK (formula oficial Huawei Cloud).
# Requiere HW_ACCESS_KEY y HW_SECRET_KEY en el entorno.
swr-login:
	@test -n "$$HW_ACCESS_KEY" && test -n "$$HW_SECRET_KEY" || \
		{ echo "!! set HW_ACCESS_KEY y HW_SECRET_KEY"; exit 1; }
	@LOGIN_KEY=$$(printf "$$HW_ACCESS_KEY" | openssl dgst -binary -sha256 -hmac "$$HW_SECRET_KEY" \
		| od -An -vtx1 | sed 's/[ \n]//g' | sed 'N;s/\n//'); \
	docker login -u "$(SWR_REGION)@$$HW_ACCESS_KEY" -p "$$LOGIN_KEY" $(SWR_HOST)

image-build:
	@echo ">> construyendo $(IMAGE)"
	docker build --provenance=false -t $(IMAGE) .
	@echo ">> construyendo $(CHATBOT_IMAGE)"
	docker build --provenance=false -f chatbot/Dockerfile -t $(CHATBOT_IMAGE) .

image-push: swr-login
	@echo ">> push $(IMAGE)"
	docker push $(IMAGE)
	@echo ">> push $(CHATBOT_IMAGE)"
	docker push $(CHATBOT_IMAGE)

image: image-build image-push
	@echo ">> imagenes publicadas:"
	@echo "   API:     $(IMAGE)"
	@echo "   Chatbot: $(CHATBOT_IMAGE)"

mirror-images: swr-login
	sh scripts/mirror-images.sh $(SWR_HOST) $(SWR_ORG)

# ---- Deploy CCE ----

# El backend S3 (OBS) usa credenciales estilo AWS; se mapean desde HW_* si
# AWS_* no esta definido (mismo patron que .github/workflows/deploy.yml).
# Los env vars *_CHECKSUM_* evitan el XAmzContentSHA256Mismatch de OBS con el
# SDK de AWS que incluye Terraform >= 1.11 (checksums CRC32 no soportados por
# backends S3-compatibles). Ver github.com/hashicorp/terraform/issues/36704.
TF_ENV = AWS_ACCESS_KEY_ID=$${AWS_ACCESS_KEY_ID:-$$HW_ACCESS_KEY} \
         AWS_SECRET_ACCESS_KEY=$${AWS_SECRET_ACCESS_KEY:-$$HW_SECRET_KEY} \
         AWS_REQUEST_CHECKSUM_CALCULATION=when_required \
         AWS_RESPONSE_CHECKSUM_VALIDATION=when_required

# Deploy end-to-end: build + push + mirror + terraform apply (dos fases).
# Fase 1: infraestructura Huawei Cloud (VPC, CCE, SWR, EIP).
# Fase 2: recursos Kubernetes (manifests, secrets, configmaps) — requiere cluster CCE existente.
# Requiere HW_ACCESS_KEY, HW_SECRET_KEY en el entorno (TF_BUCKET tiene default).
deploy: image mirror-images
	@echo ">> terraform init (image_tag=$(IMAGE_TAG))..."
	cd terraform && $(TF_ENV) terraform init -force-copy \
		-backend-config="bucket=$(TF_BUCKET)" \
		-backend-config="region=$(SWR_REGION)" \
		-backend-config="endpoint=https://obs.$(SWR_REGION).myhuaweicloud.com" \
		-backend-config="skip_region_validation=true" \
		-backend-config="skip_credentials_validation=true" \
		-backend-config="skip_metadata_api_check=true" \
		-backend-config="skip_requesting_account_id=true"
	@echo ">> fase 1: infraestructura Huawei Cloud (CCE, VPC, SWR)..."
	cd terraform && $(TF_ENV) terraform apply -auto-approve \
		-target=huaweicloud_vpc.agent \
		-target=huaweicloud_vpc_subnet.agent \
		-target=huaweicloud_networking_secgroup.agent \
		-target=huaweicloud_networking_secgroup_rule.ingress_vpc \
		-target=huaweicloud_networking_secgroup_rule.egress_all \
		-target=huaweicloud_vpc_eip.cce_master \
		-target=huaweicloud_cce_cluster.agent \
		-target=huaweicloud_cce_node_pool.agent \
		-target=huaweicloud_swr_organization.agent \
		-target=huaweicloud_swr_repository.api \
		-target=huaweicloud_swr_repository.chatbot \
		-target=random_password.node_pool \
		-target=local_file.kubeconfig \
		-var="image_tag=$(IMAGE_TAG)"
	@echo ">> fase 2: recursos Kubernetes (manifests, secrets, configmaps)..."
	cd terraform && $(TF_ENV) terraform apply -auto-approve -var="image_tag=$(IMAGE_TAG)"

# Legacy: aplica manifiestos deploy/cce/ con kubectl (fuente alternativa).
# Los manifiestos usan placeholders ${...}; este target los renderiza con envsubst.
# Requiere SWR_HOST y SWR_ORG en el entorno (o usa los defaults del Makefile).
deploy-cce:
	@echo ">> creando ConfigMaps de SQL..."
	sh deploy/cce/create-configmaps.sh data-analyst-agent
	@echo ">> creando Secrets..."
	@cp deploy/cce/01-secrets.yaml.example deploy/cce/01-secrets.yaml 2>/dev/null || true
	@export namespace=data-analyst-agent; \
	envsubst < deploy/cce/01-secrets.yaml | kubectl apply -f - || \
		echo "!! edita deploy/cce/01-secrets.yaml con tus credenciales reales"
	@echo ">> aplicando manifests (envsubst)..."
	export namespace=data-analyst-agent \
		api_image=$(SWR_HOST)/$(SWR_ORG)/analyst-api:$(IMAGE_TAG) \
		chatbot_image=$(SWR_HOST)/$(SWR_ORG)/analyst-chatbot:$(IMAGE_TAG) \
		postgres_image=$(SWR_HOST)/$(SWR_ORG)/postgres:16 \
		redis_image=$(SWR_HOST)/$(SWR_ORG)/redis:7 \
		ollama_image=$(SWR_HOST)/$(SWR_ORG)/ollama:latest \
		litellm_image=$(SWR_HOST)/$(SWR_ORG)/litellm:latest \
		api_replicas=2; \
	for f in 00-namespace 02-configmaps 03-pvcs 10-postgres-agent 11-postgres-analytics \
	         12-redis 13-ollama 14-ollama-init-job 15-litellm 16-api 17-elb \
	         18-mcp-glossary 19-mcp-explorer 20-chatbot 21-litellm-db-redis \
	         22-elb-chatbot 23-elb-litellm; do \
		envsubst < deploy/cce/$$f.yaml | kubectl apply -f -; \
	done
	@echo ">> deploy aplicado. EIPs:"
	@echo "   API:    $$(kubectl get svc api-elb -n data-analyst-agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo '(pendiente)')"
	@echo "   Chatbot:$$(kubectl get svc chatbot-elb -n data-analyst-agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo '(pendiente)')"
	@echo "   LiteLLM:$$(kubectl get svc litellm-elb -n data-analyst-agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo '(pendiente)')"

# ---- Terraform (Huawei Cloud CCE) ----

tf-init:
	cd terraform && $(TF_ENV) terraform init -force-copy \
		-backend-config="bucket=$(TF_BUCKET)" \
		-backend-config="region=$(SWR_REGION)" \
		-backend-config="endpoint=https://obs.$(SWR_REGION).myhuaweicloud.com" \
		-backend-config="skip_region_validation=true" \
		-backend-config="skip_credentials_validation=true" \
		-backend-config="skip_metadata_api_check=true" \
		-backend-config="skip_requesting_account_id=true"

tf-plan:
	cd terraform && $(TF_ENV) terraform plan

tf-apply:
	cd terraform && $(TF_ENV) terraform apply -auto-approve

tf-destroy:
	cd terraform && $(TF_ENV) terraform destroy -auto-approve

# ---- Limpieza ----

clean:
	docker compose down -v --remove-orphans
	@echo ">> contenedores y volúmenes eliminados"

clean-images:
	@echo ">> eliminando imágenes Docker del proyecto..."
	-docker rmi $(IMAGE) 2>/dev/null
	-docker rmi $(CHATBOT_IMAGE) 2>/dev/null
	-docker image prune -f
	@echo ">> imágenes eliminadas"

clean-tf:
	@test -n "$$HW_ACCESS_KEY" && test -n "$$HW_SECRET_KEY" || \
		{ echo "!! set HW_ACCESS_KEY y HW_SECRET_KEY"; exit 1; }
	@echo ">> eliminando subnet..."
	$(TF_ENV) terraform -chdir=terraform destroy -auto-approve \
		-target=huaweicloud_vpc_subnet.agent
	@echo ">> eliminando VPC..."
	$(TF_ENV) terraform -chdir=terraform destroy -auto-approve \
		-target=huaweicloud_vpc.agent
	@echo ">> recursos eliminados (VPC + subnet)"

clean-all: clean clean-images clean-tf
	@echo ">> limpieza completa"