#!/usr/bin/env bash
# Tests of scripts/pull-models.sh with a fake `docker` on the PATH (no Docker, no network).
# The models are pulled into the Ollama container of the VM, which is found by its compose labels
# (ADR-0004) or named in OLLAMA_CONTAINER.
#
# Usage: tests/shell/test-pull-models.sh        (exit 0 when every test passes)
#
# No `set -e` on purpose: every case is run to the end so that all failures are counted.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
script="${root}/scripts/pull-models.sh"
work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT

failures=0
checks=0

# A fake docker: `ps -q --filter label=...` finds the container, `exec <id> ollama list|pull X` and
# `exec <id> df -Pk ...` answer for it. FAKE_INSTALLED lists installed models, FAKE_FREE_KB the free
# disk, FAKE_DOWN=1 = Docker does not answer, FAKE_NO_OLLAMA=1 = no Ollama container,
# FAKE_FAIL_PULL names a model whose pull fails. Every call is appended to ${work}/calls.
mkdir -p "${work}/bin"
cat >"${work}/bin/docker" <<'FAKE'
#!/usr/bin/env bash
echo "$*" >>"${FAKE_CALLS}"
[[ "${FAKE_DOWN:-0}" == "1" ]] && exit 1
case "$*" in
"ps -q"*)
    [[ "${FAKE_NO_OLLAMA:-0}" == "1" ]] || echo "ollama-container-id"
    ;;
*"ollama list"*)
    echo "NAME ID SIZE MODIFIED"
    for name in ${FAKE_INSTALLED:-}; do echo "${name} abc 2GB now"; done
    ;;
*"df -Pk"*)
    echo "Filesystem 1024-blocks Used Available Capacity Mounted"
    echo "x 100 1 ${FAKE_FREE_KB:-83886080} 1% /root/.ollama"
    ;;
*"ollama pull "*)
    [[ "$*" == *"ollama pull ${FAKE_FAIL_PULL:-none}" ]] && exit 1
    echo "pulled"
    ;;
esac
FAKE
chmod +x "${work}/bin/docker"
printf '%s\n' '# comment' 'llama3.2:3b' '' 'phi3.5  # inline' >"${work}/models.txt"

run() {
    : >"${work}/calls"
    env PATH="${work}/bin:${PATH}" FAKE_CALLS="${work}/calls" "$@" \
        bash "${script}" "${work}/models.txt" >"${work}/out" 2>&1
}

expect() {
    local name="$1" want="$2" got="$3"
    checks=$((checks + 1))
    if [[ "${got}" != "${want}" ]]; then
        echo "FAIL ${name}: wanted '${want}', got '${got}'"
        failures=$((failures + 1))
    fi
}

pulls() { grep -c "ollama pull" "${work}/calls" || true; }
calls_matching() { grep -c -- "$1" "${work}/calls" || true; }

run FAKE_INSTALLED=""
expect "pulls both models, exit 0" "0" "$?"
expect "pulls both models, count" "2" "$(pulls)"
expect "the container is found by the compose labels" "1" "$(calls_matching 'label=com.docker.compose.project=ollama')"
expect "the pull goes to the container that was found" "2" "$(calls_matching 'exec ollama-container-id ollama pull')"

run FAKE_INSTALLED="llama3.2:3b phi3.5:latest"
expect "everything installed, exit 0" "0" "$?"
expect "everything installed, no pull" "0" "$(pulls)"

run FAKE_INSTALLED="llama3.2:3b"
expect "one installed, exit 0" "0" "$?"
expect "one installed, one pull" "1" "$(pulls)"

run FAKE_FREE_KB=1000
expect "too little disk, exit 2" "2" "$?"
expect "too little disk, nothing pulled" "0" "$(pulls)"

run FAKE_FREE_KB=1000 MIN_FREE_GB=0
expect "limit lowered, exit 0" "0" "$?"

run FAKE_DOWN=1
expect "docker does not answer, exit 3" "3" "$?"

run FAKE_NO_OLLAMA=1
expect "no ollama container, exit 3" "3" "$?"
expect "no ollama container, says what to do" "1" "$(grep -c 'OLLAMA_CONTAINER' "${work}/out" || true)"

run FAKE_FAIL_PULL=phi3.5
expect "pull fails, exit 1" "1" "$?"

run OLLAMA_CONTAINER=my-ollama
expect "named container, exit 0" "0" "$?"
expect "named container, no label search" "0" "$(calls_matching 'ps -q')"
expect "named container, used for the pulls" "2" "$(calls_matching 'exec my-ollama ollama pull')"

run OLLAMA_PROJECT=other OLLAMA_SERVICE=model-server
expect "other project and service, exit 0" "0" "$?"
expect "other project and service, searched by their labels" "1" "$(calls_matching 'label=com.docker.compose.service=model-server')"

: >"${work}/empty.txt"
env PATH="${work}/bin:${PATH}" FAKE_CALLS="${work}/calls" bash "${script}" "${work}/empty.txt" >/dev/null 2>&1
expect "empty list, exit 1" "1" "$?"

env PATH="${work}/bin:${PATH}" FAKE_CALLS="${work}/calls" bash "${script}" "${work}/missing.txt" >/dev/null 2>&1
expect "missing file, exit 1" "1" "$?"

if ((failures > 0)); then
    echo "${failures} of ${checks} checks failed"
    exit 1
fi
echo "all ${checks} checks passed"
