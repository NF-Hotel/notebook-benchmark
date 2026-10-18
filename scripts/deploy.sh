#!/usr/bin/env bash
# Build and start the benchmark service and Ollama (MIL-003, deploy/docker-compose.yml) and
# wait until both are healthy. Changes state: it builds an image and starts containers;
# running it is the explicit act, and a second run only updates what changed.
# Pull the models afterwards with scripts/pull-models.sh.
#
# Usage: scripts/deploy.sh
#
# Environment:
#   BENCHMARK_ENV  env file of the benchmark service (default deploy/benchmark.env)
#   DEPLOY_WAIT_S  seconds to wait for both services to be healthy (default 180)
#   COMPOSE_FILE   compose file (default deploy/docker-compose.yml)
#   OLLAMA_ENV     env file for the compose file (default deploy/ollama.env)
#
# Exit codes: 0 both healthy; 1 a setting or a prerequisite is missing, or a service is not
# healthy in time.
# Needs: bash 4 or later, docker compose v2 (--wait), grep, cut.
set -euo pipefail

# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

deploy="${root}/deploy"
benchmark_env="${BENCHMARK_ENV:-${deploy}/benchmark.env}"
wait_s="${DEPLOY_WAIT_S:-180}"

[[ -f "${benchmark_env}" ]] \
    || fail "${benchmark_env} is missing; copy deploy/benchmark.env.example and fill it in"
[[ -f "${env_file}" ]] \
    || fail "${env_file} is missing; copy deploy/ollama.env.example and fill it in"

for name in NFBENCH_API_TOKEN NFBENCH_WEB_TOKEN; do
    value="$(grep -E "^${name}=" "${benchmark_env}" | head -n 1 | cut -d= -f2- || true)"
    if [[ -z "${value}" || "${value}" == "change-me" ]]; then
        fail "${name} in ${benchmark_env} is empty or still change-me (make one: openssl rand -hex 32)"
    fi
done

network="$(grep -E '^NFHOTEL_API_NETWORK=' "${env_file}" | head -n 1 | cut -d= -f2- || true)"
network="${network:-nfhotel-api}"
docker network inspect "${network}" >/dev/null 2>&1 \
    || fail "the Docker network ${network} does not exist; create it once: docker network create --internal ${network}"

BENCHMARK_ENV_FILE="${benchmark_env}" compose up -d --build --wait --wait-timeout "${wait_s}" \
    || fail "a service is not healthy after ${wait_s} seconds; see: docker compose -f deploy/docker-compose.yml logs"

echo "benchmark and ollama are healthy. Next: scripts/pull-models.sh, then scripts/smoke-test.sh"
