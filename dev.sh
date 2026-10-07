#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Atajo para el stack LOCAL de Voraz.
#
#    ./dev.sh              → levanta backend + erp_service + ia_service + mongo
#    ./dev.sh up -d        → lo mismo
#    ./dev.sh ps           → estado
#    ./dev.sh logs -f backend
#    ./dev.sh build backend
#    ./dev.sh down         → apaga (los datos de Mongo quedan en el volumen)
#
#  Siempre usa docker-compose.yml (base, = producción) + docker-compose.local.yml.
#  Nunca invoques docker-compose.yml solo: esa es la configuración de producción.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

readonly SERVICIOS_LOCALES="backend erp_service ia_service mongo"
readonly COMPOSE_ARGS=(-f docker-compose.yml -f docker-compose.local.yml --env-file .env.local)

if [ $# -eq 0 ] || { [ "$1" = "up" ] && [ $# -le 1 ]; }; then
  echo ">>> Levantando el stack local: $SERVICIOS_LOCALES"
  exec docker compose "${COMPOSE_ARGS[@]}" up -d $SERVICIOS_LOCALES
fi

exec docker compose "${COMPOSE_ARGS[@]}" "$@"
