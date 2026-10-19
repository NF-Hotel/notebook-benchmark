# shellcheck shell=bash
# Shared by deploy.sh, pull-models.sh and smoke-test.sh (sourced, never run on its own).
# Defines the repository root, the compose file and the settings file, `compose` and `fail`.
#
# Environment: COMPOSE_FILE    compose file (default deploy/docker-compose.yml)
#              BENCHMARK_ENV   settings file of the service, also read by compose for the names of
#                              the networks (default deploy/benchmark.env)
# Needs: bash 4 or later, docker with the compose plugin (v2).

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="${COMPOSE_FILE:-${root}/deploy/docker-compose.yml}"
env_file="${BENCHMARK_ENV:-${root}/deploy/benchmark.env}"

# Run docker compose on the compose file of this project, with the one settings file.
compose() {
    BENCHMARK_ENV_FILE="${env_file}" docker compose -f "${compose_file}" --env-file "${env_file}" "$@"
}

# Print an error to standard error and stop with exit code 1.
fail() {
    echo "error: $*" >&2
    exit 1
}
