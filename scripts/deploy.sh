#!/usr/bin/env bash
# Build and start the benchmark service (MIL-003, deploy/docker-compose.yml) and wait until it is
# healthy. It uses the Ollama that NFHotel runs on the same VM (ADR-0004), so the network of that
# Ollama and the internal network of the web application and API must exist. Changes state: it
# builds an image and starts a container; running it is the explicit act, and a second run only
# updates what changed. Pull the models afterwards with scripts/pull-models.sh.
#
# Usage: scripts/deploy.sh
#
# Environment:
#   BENCHMARK_ENV  settings file of the service (default deploy/benchmark.env)
#   DEPLOY_WAIT_S  seconds to wait for the service to be healthy (default 180)
#   COMPOSE_FILE   compose file (default deploy/docker-compose.yml)
#
# Exit codes: 0 healthy; 1 a setting or a prerequisite is missing, or the service is not healthy
# in time.
# Needs: bash 4 or later, docker compose v2 (--wait), grep, cut.
set -euo pipefail

# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

wait_s="${DEPLOY_WAIT_S:-180}"

[[ -f "${env_file}" ]] \
    || fail "${env_file} is missing; copy deploy/benchmark.env.example and fill it in"

# The value of a setting in the settings file, or the default when it is not there.
setting() {
    local value
    value="$(grep -E "^$1=" "${env_file}" | head -n 1 | cut -d= -f2- || true)"
    printf '%s\n' "${value:-$2}"
}

for name in NFBENCH_API_TOKEN NFBENCH_WEB_TOKEN; do
    value="$(setting "${name}" "")"
    if [[ -z "${value}" || "${value}" == "change-me" ]]; then
        fail "${name} in ${env_file} is empty or still change-me (make one: openssl rand -hex 32)"
    fi
done

api_network="$(setting NFHOTEL_API_NETWORK nfhotel-api)"
llm_network="$(setting NFHOTEL_LLM_NETWORK nfhotel-llm)"
docker network inspect "${api_network}" >/dev/null 2>&1 \
    || fail "the Docker network ${api_network} does not exist; NFHotel makes it, or create it once: docker network create --internal ${api_network}"
docker network inspect "${llm_network}" >/dev/null 2>&1 \
    || fail "the Docker network ${llm_network} does not exist; deploy NFHotel's Ollama first (scripts/deploy-services.sh ollama in the NFHotel checkout)"

compose up -d --build --wait --wait-timeout "${wait_s}" \
    || fail "the service is not healthy after ${wait_s} seconds; see: docker compose -f deploy/docker-compose.yml logs"

echo "benchmark is healthy. Next: scripts/pull-models.sh, then scripts/smoke-test.sh"
