#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Atajo para el stack LOCAL de Voraz.
#
#    ./dev.sh              → levanta backend + erp_service + ia_service + mongo
#    ./dev.sh up -d        → lo mismo
#    ./dev.sh up backend   → solo ese servicio
#    ./dev.sh ps           → estado
#    ./dev.sh logs -f backend
#    ./dev.sh build backend
#    ./dev.sh down         → apaga (los datos de Mongo quedan en el volumen)
#
#  Siempre usa docker-compose.yml (base, = producción) + docker-compose.local.yml.
#  Nunca invoques docker-compose.yml solo: esa es la configuración de producción.
#
#  IMPORTANTE: `up` sin nombres de servicio levanta SOLO el slice local. Nunca
#  levanta dashwhat2: una segunda sesión de WhatsApp puede invalidar la de prod.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

readonly SERVICIOS_LOCALES="backend erp_service ia_service mongo"
readonly COMPOSE_ARGS=(-f docker-compose.yml -f docker-compose.local.yml --env-file .env.local)

case "${1:-}" in
  "" | up)
    shift || true
    # Se separan los flags (-d, --detach) de los nombres de servicio
    servicios=()
    for a in "$@"; do
      case "$a" in
        -d|--detach) ;;
        *) servicios+=("$a") ;;
      esac
    done
    if [ ${#servicios[@]} -eq 0 ]; then
      echo ">>> Levantando el stack local: $SERVICIOS_LOCALES"
      read -r -a servicios <<< "$SERVICIOS_LOCALES"
    fi
    exec docker compose "${COMPOSE_ARGS[@]}" up -d "${servicios[@]}"
    ;;
  *)
    exec docker compose "${COMPOSE_ARGS[@]}" "$@"
    ;;
esac
