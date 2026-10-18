# shellcheck shell=bash
# Shared by deploy.sh, pull-models.sh and smoke-test.sh (sourced, never run on its own).
# Defines the repository root, the compose file and env file, `compose` and `fail`.
#
# Environment: COMPOSE_FILE  compose file (default deploy/docker-compose.yml)
#              OLLAMA_ENV    env file read by the compose file (default deploy/ollama.env)
# Needs: bash 4 or later, docker with the compose plugin (v2).

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="${COMPOSE_FILE:-${root}/deploy/docker-compose.yml}"
env_file="${OLLAMA_ENV:-${root}/deploy/ollama.env}"

# Run docker compose on the compose file of this project.
compose() {
    docker compose -f "${compose_file}" --env-file "${env_file}" "$@"
}

# Print an error to standard error and stop with exit code 1.
fail() {
    echo "error: $*" >&2
    exit 1
}
