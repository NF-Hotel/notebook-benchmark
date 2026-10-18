#!/usr/bin/env bash
# Pull the models of deploy/models.txt into the Ollama container, one at a time (MIL-003,
# ADR-0002). Changes state: it downloads models into the Ollama volume; running it is the
# explicit act, and a model that is installed is skipped, so it is safe to run again.
#
# Usage: scripts/pull-models.sh [models-file]
#
# Environment:
#   MIN_FREE_GB   free disk the Ollama volume must have before anything is pulled (default 20)
#   COMPOSE_FILE  compose file (default deploy/docker-compose.yml)
#   OLLAMA_ENV    env file for the compose file (default deploy/ollama.env)
#
# Exit codes: 0 all models installed; 1 a pull failed or the input is wrong;
#             2 not enough free disk, nothing was pulled; 3 Ollama is not running.
# Needs: bash 4 or later (mapfile), docker compose v2, awk.
set -euo pipefail

# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

models_file="${1:-${root}/deploy/models.txt}"
min_free_gb="${MIN_FREE_GB:-20}"

read_models() {
    local line
    while IFS= read -r line || [[ -n "${line}" ]]; do
        line="${line%%#*}"
        line="${line//[$'\t\r ']/}"
        [[ -n "${line}" ]] && printf '%s\n' "${line}"
    done <"${models_file}"
}

installed_models() {
    compose exec -T ollama ollama list | awk 'NR > 1 { print $1 }'
}

is_installed() {
    local wanted="$1" name
    while IFS= read -r name; do
        if [[ "${name}" == "${wanted}" || "${name}" == "${wanted}:latest" ]]; then
            return 0
        fi
    done <<<"${installed}"
    return 1
}

[[ -f "${models_file}" ]] || fail "models file not found: ${models_file}"
mapfile -t models < <(read_models)
((${#models[@]} > 0)) || fail "no model in ${models_file}"

if ! installed="$(installed_models 2>/dev/null)"; then
    echo "error: the ollama container is not running; start it with scripts/deploy.sh" >&2
    exit 3
fi

free_kb="$(compose exec -T ollama df -Pk /root/.ollama | awk 'NR == 2 { print $4 }')"
[[ "${free_kb}" =~ ^[0-9]+$ ]] || fail "could not read the free disk of the Ollama volume"
free_gb=$((free_kb / 1024 / 1024))
if ((free_gb < min_free_gb)); then
    echo "error: ${free_gb} GB free on the Ollama volume, ${min_free_gb} GB needed; nothing pulled" >&2
    exit 2
fi

for model in "${models[@]}"; do
    if is_installed "${model}"; then
        echo "skip ${model}: already installed"
        continue
    fi
    echo "pull ${model}"
    compose exec -T ollama ollama pull "${model}" || fail "pulling ${model} failed"
done
echo "done: ${#models[@]} model(s) in ${models_file} are installed"
