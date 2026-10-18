#!/usr/bin/env bash
# Smoke test of the running benchmark service (MIL-003): health, the guarded API, and a short
# run to the state `done`. The calls are made inside the benchmark container, so no host port is
# needed and the token never leaves the container. It starts one real run (it loads a model
# into memory); that is the explicit act of running it.
#
# Usage: scripts/smoke-test.sh [--model NAME] [--restart-check]
#   --model NAME      model to run (default: the first installed model)
#   --restart-check   after the run, restart the container and check that an undelivered
#                     result is still on the volume (needs a web API that is not answering)
#
# Environment:
#   SMOKE_TIMEOUT_S  seconds to wait for the run (default 900)
#   COMPOSE_FILE     compose file (default deploy/docker-compose.yml)
#   OLLAMA_ENV       env file for the compose file (default deploy/ollama.env)
#
# Exit codes: 0 all checks passed; 1 a check failed or an option is wrong; 3 no model is
# installed (run scripts/pull-models.sh first).
# Needs: bash 4 or later, docker compose v2, sed.
set -euo pipefail

# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage="usage: scripts/smoke-test.sh [--model NAME] [--restart-check]"
model=""
restart_check=0

while (($# > 0)); do
    case "$1" in
        --model) model="${2:?${usage}}"; shift 2 ;;
        --restart-check) restart_check=1; shift ;;
        *) fail "unknown option $1; ${usage}" ;;
    esac
done

# Runs in the container: 1 = a check failed, 3 = no model installed.
read -r -d '' probe <<'PY' || true
import json, os, sys, time, urllib.error, urllib.request

base = "http://127.0.0.1:8000"
token = os.environ["NFBENCH_API_TOKEN"]
wanted = sys.argv[1]
timeout_s = float(sys.argv[2])


def call(method, path, body=None, auth=True):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if auth:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, None


def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        sys.exit(1)


status, _ = call("GET", "/health", auth=False)
check("health answers 200 without a token", status == 200)
status, _ = call("GET", "/models", auth=False)
check("models without a token gets 401", status == 401)
status, _ = call("POST", "/runs", {"models": ["x"]}, auth=False)
check("start without a token gets 401", status == 401)

status, body = call("GET", "/models")
check("models with the token answers 200", status == 200)
models = body["models"]
if not models:
    print("no model is installed; run scripts/pull-models.sh")
    sys.exit(3)
model = wanted or models[0]
check("the model " + model + " is installed", model in models)

status, body = call("POST", "/runs", {"models": [model], "hotel_analysis": True, "runs": 1})
check("start answers 202", status == 202)
run_id = body["run_id"]
print("run", run_id)

deadline = time.monotonic() + timeout_s
state = body["state"]
while state not in ("done", "failed") and time.monotonic() < deadline:
    time.sleep(5)
    status, body = call("GET", "/runs/" + run_id)
    state = body["state"]
check("the run reaches done (state: " + state + ")", state == "done")
print("delivery:", body["delivery"])
print("RUN_ID=" + run_id)
print("DELIVERY=" + body["delivery"])
PY

echo "== smoke test of the benchmark service"
set +e
output="$(compose exec -T benchmark python -c "${probe}" "${model}" "${SMOKE_TIMEOUT_S:-900}")"
status=$?
set -e
echo "${output}"
((status == 0)) || exit "${status}"

if ((restart_check == 1)); then
    run_id="$(sed -n 's/^RUN_ID=//p' <<<"${output}")"
    delivery="$(sed -n 's/^DELIVERY=//p' <<<"${output}")"
    [[ "${delivery}" == "pending" ]] || {
        echo "FAIL --restart-check needs delivery pending, got ${delivery}" >&2
        exit 1
    }
    compose restart benchmark >/dev/null
    compose up -d --wait --wait-timeout 120 benchmark >/dev/null
    if compose exec -T benchmark test -f "/data/pending/${run_id}.json"; then
        echo "ok   the undelivered result survived the restart"
    else
        echo "FAIL the undelivered result is gone after the restart" >&2
        exit 1
    fi
fi
echo "smoke test passed"
