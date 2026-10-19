#!/usr/bin/env bash
# Pull the models of deploy/models.txt into the Ollama container of the VM, one at a time (MIL-003,
# ADR-0002, ADR-0004). The Ollama is the one that NFHotel runs (deploy/ollama, compose project and
# service `ollama`), found by its compose labels. Changes state: it downloads models into that
# container's volume; running it is the explicit act, and a model that is installed is skipped, so
# it is safe to run again.
#
# Usage: scripts/pull-models.sh [models-file]
#
# Environment:
#   MIN_FREE_GB       free disk the Ollama volume must have before anything is pulled (default 20)
#   OLLAMA_CONTAINER  name or id of the Ollama container; skips the search by label
#   OLLAMA_PROJECT    compose project of the Ollama container (default ollama)
#   OLLAMA_SERVICE    compose service of the Ollama container (default ollama)
#
# Exit codes: 0 all models installed; 1 a pull failed or the input is wrong;
#             2 not enough free disk, nothing was pulled; 3 no Ollama container could be reached.
# Needs: bash 4 or later (mapfile), docker, awk.
set -euo pipefail

# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

models_file="${1:-${root}/deploy/models.txt}"
min_free_gb="${MIN_FREE_GB:-20}"
ollama_project="${OLLAMA_PROJECT:-ollama}"
ollama_service="${OLLAMA_SERVICE:-ollama}"

read_models() {
    local line
    while IFS= read -r line || [[ -n "${line}" ]]; do
        line="${line%%#*}"
        line="${line//[$'\t\r ']/}"
        [[ -n "${line}" ]] && printf '%s\n' "${line}"
    done <"${models_file}"
}

# The Ollama container: the one named in OLLAMA_CONTAINER, else the first running container with the
# compose labels of NFHotel's deploy/ollama. Prints nothing when there is none.
find_ollama() {
    if [[ -n "${OLLAMA_CONTAINER:-}" ]]; then
        printf '%s\n' "${OLLAMA_CONTAINER}"
        return 0
    fi
    docker ps -q \
        --filter "label=com.docker.compose.project=${ollama_project}" \
        --filter "label=com.docker.compose.service=${ollama_service}" | head -n 1
}

ollama_exec() {
    docker exec "${container}" "$@"
}

installed_models() {
    ollama_exec ollama list | awk 'NR > 1 { print $1 }'
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

container="$(find_ollama 2>/dev/null)" || container=""
if [[ -z "${container}" ]]; then
    echo "error: no running Ollama container (project ${ollama_project}, service ${ollama_service}); deploy NFHotel's ollama first, or name it with OLLAMA_CONTAINER" >&2
    exit 3
fi

if ! installed="$(installed_models 2>/dev/null)"; then
    echo "error: the Ollama container ${container} does not answer; check: docker logs ${container}" >&2
    exit 3
fi

free_kb="$(ollama_exec df -Pk /root/.ollama | awk 'NR == 2 { print $4 }')"
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
    ollama_exec ollama pull "${model}" || fail "pulling ${model} failed"
done
echo "done: ${#models[@]} model(s) in ${models_file} are installed"
