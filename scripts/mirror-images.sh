#!/bin/sh
# Hace mirror de imagenes publicas a SWR para que los nodos CCE
# no necesiten acceso a Docker Hub / ghcr.io.
#
# Uso: sh scripts/mirror-images.sh <swr_host> <swr_org>
# Ej:   sh scripts/mirror-images.sh swr.la-north-2.myhuaweicloud.com langchain-test

set -e

SWR_HOST="$1"
SWR_ORG="$2"

if [ -z "$SWR_HOST" ] || [ -z "$SWR_ORG" ]; then
  echo "Uso: sh scripts/mirror-images.sh <swr_host> <swr_org>"
  exit 1
fi

MIRROR() {
  SRC="$1"
  DST="$2"
  echo ">> mirror $SRC -> $DST"
  docker pull "$SRC"
  docker tag  "$SRC" "$DST"
  docker push "$DST"
}

MIRROR "postgres:16"                          "$SWR_HOST/$SWR_ORG/postgres:16"
MIRROR "redis:7"                              "$SWR_HOST/$SWR_ORG/redis:7"
MIRROR "ollama/ollama:latest"                 "$SWR_HOST/$SWR_ORG/ollama:latest"
MIRROR "ghcr.io/berriai/litellm:main-latest"  "$SWR_HOST/$SWR_ORG/litellm:latest"

echo ">> mirror completo"
