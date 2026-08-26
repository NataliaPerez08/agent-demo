#!/bin/sh
# Genera los ConfigMaps de inicializacion SQL (agent DB + analytics DB)
# desde los archivos del repositorio. Fuente unica de verdad: database/.
#
# Uso (desde la raiz del repo, con kubeconfig apuntando a CCE):
#   sh deploy/cce/create-configmaps.sh

set -e

NS="${1:-data-analyst-agent}"

kubectl create configmap agent-db-init \
  --namespace="$NS" \
  --from-file=001_audit.sql=database/agent/ddl/001_audit.sql \
  --from-file=002_dashboards.sql=database/agent/ddl/002_dashboards.sql \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap analytics-db-init \
  --namespace="$NS" \
  --from-file=001_schema.sql=database/analytics/ddl/001_schema.sql \
  --from-file=002_indexes.sql=database/analytics/ddl/002_indexes.sql \
  --from-file=003_views.sql=database/analytics/ddl/003_views.sql \
  --from-file=004_agent_role.sql=database/analytics/ddl/004_agent_role.sql \
  --from-file=005_seed.sql=database/analytics/dml/001_seed.sql \
  --dry-run=client -o yaml | kubectl apply -f -
