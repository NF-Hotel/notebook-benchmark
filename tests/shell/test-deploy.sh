#!/usr/bin/env bash
# Tests of scripts/deploy.sh and the option handling of scripts/smoke-test.sh with a fake
# `docker` on the PATH (no Docker, no network).
#
# Usage: tests/shell/test-deploy.sh        (exit 0 when every test passes)
#
# No `set -e` on purpose: every script is run to the end so that all failures are counted.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT

failures=0
checks=0

# FAKE_NO_NETWORK=<name>: `docker network inspect <name>` fails. FAKE_UNHEALTHY=1: `compose up` fails.
mkdir -p "${work}/bin"
cat >"${work}/bin/docker" <<'FAKE'
#!/usr/bin/env bash
echo "$*" >>"${FAKE_CALLS}"
case "$*" in
"network inspect"*) [[ "$*" == *" ${FAKE_NO_NETWORK:-none}" ]] && exit 1 ;;
*" up "*) [[ "${FAKE_UNHEALTHY:-0}" == "1" ]] && exit 1 ;;
esac
exit 0
FAKE
chmod +x "${work}/bin/docker"
: >"${work}/compose.yml"

# The one settings file: the two tokens, and the names of the two Docker networks that it joins.
write_benchmark_env() {
    printf '%s\n' "NFBENCH_API_TOKEN=$1" "NFBENCH_WEB_TOKEN=$2" \
        'NFHOTEL_API_NETWORK=test-api' 'NFHOTEL_LLM_NETWORK=test-llm' >"${work}/benchmark.env"
}

deploy() {
    : >"${work}/calls"
    env PATH="${work}/bin:${PATH}" FAKE_CALLS="${work}/calls" COMPOSE_FILE="${work}/compose.yml" \
        BENCHMARK_ENV="${work}/benchmark.env" "$@" \
        bash "${root}/scripts/deploy.sh" >"${work}/out" 2>&1
}

expect() {
    local name="$1" want="$2" got="$3"
    checks=$((checks + 1))
    if [[ "${got}" != "${want}" ]]; then
        echo "FAIL ${name}: wanted '${want}', got '${got}'"
        failures=$((failures + 1))
    fi
}

ups() { grep -c " up " "${work}/calls" || true; }

write_benchmark_env real-api-token real-web-token
deploy
expect "good settings, exit 0" "0" "$?"
expect "good settings, compose up once" "1" "$(ups)"
expect "the network of the web application is checked" "1" "$(grep -c 'network inspect test-api' "${work}/calls" || true)"
expect "the network of Ollama is checked" "1" "$(grep -c 'network inspect test-llm' "${work}/calls" || true)"
expect "compose reads the one settings file" "1" "$(grep -c -- "--env-file ${work}/benchmark.env" "${work}/calls" || true)"

write_benchmark_env change-me real-web-token
deploy
expect "api token change-me, exit 1" "1" "$?"
expect "api token change-me, nothing started" "0" "$(ups)"

write_benchmark_env real-api-token ""
deploy
expect "empty web token, exit 1" "1" "$?"

rm -f "${work}/benchmark.env"
deploy
expect "benchmark.env missing, exit 1" "1" "$?"
expect "benchmark.env missing, says what to copy" "1" "$(grep -c 'benchmark.env.example' "${work}/out" || true)"

write_benchmark_env real-api-token real-web-token
deploy FAKE_NO_NETWORK=test-api
expect "web network missing, exit 1" "1" "$?"
expect "web network missing, nothing started" "0" "$(ups)"
expect "web network missing, says how to create it" "1" "$(grep -c 'docker network create --internal test-api' "${work}/out" || true)"

deploy FAKE_NO_NETWORK=test-llm
expect "ollama network missing, exit 1" "1" "$?"
expect "ollama network missing, nothing started" "0" "$(ups)"
expect "ollama network missing, says to deploy ollama first" "1" "$(grep -c 'scripts/deploy-services.sh ollama' "${work}/out" || true)"

deploy FAKE_UNHEALTHY=1
expect "service not healthy, exit 1" "1" "$?"

: >"${work}/calls"
env PATH="${work}/bin:${PATH}" FAKE_CALLS="${work}/calls" COMPOSE_FILE="${work}/compose.yml" \
    BENCHMARK_ENV="${work}/benchmark.env" bash "${root}/scripts/smoke-test.sh" --bogus >"${work}/out" 2>&1
expect "smoke test unknown option, exit 1" "1" "$?"
expect "smoke test unknown option, usage line" "1" "$(grep -c '^error: unknown option --bogus; usage:' "${work}/out" || true)"

if ((failures > 0)); then
    echo "${failures} of ${checks} checks failed"
    exit 1
fi
echo "all ${checks} checks passed"
