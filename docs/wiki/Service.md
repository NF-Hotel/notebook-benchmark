# The benchmark service

The benchmark also runs as a service on the Proxmox VM: an HTTP API that starts a run of local models in Ollama, and delivers the result to the NFHotel web API, which stores it for the back office. The contract is [ADR-0001](https://github.com/NF-Hotel/notebook-benchmark/blob/main/docs/adr/adr-0001-service-contract.md) and `openapi/benchmark-contract.yaml`; the models are in ADR-0002.

## Start the service

The service runs beside NFHotel on the same VM and uses the Ollama that NFHotel runs there (ADR-0004); it starts no Ollama of its own. It needs Docker with the compose plugin and the two Docker networks that NFHotel makes: `nfhotel-api` (internal, the web application and API) and `nfhotel-llm` (the Ollama). `scripts/deploy-services.sh` of NFHotel creates both.

```bash
cp deploy/benchmark.env.example deploy/benchmark.env     # set the two tokens: openssl rand -hex 32
scripts/deploy.sh
```

`scripts/deploy.sh` refuses to start while a token is empty or `change-me`, checks that both networks exist, builds the image, starts the `benchmark` container (compose project `nfbench`) and waits until it is healthy. No host port is published: the web application reaches the service at `http://benchmark:8000` on the shared network, and the service reaches the NFHotel API at the address in `NFBENCH_WEB_URL`.

## Install the models

The models are pulled into the Ollama container of NFHotel. In that container `OLLAMA_MAX_LOADED_MODELS=1` and `OLLAMA_NUM_PARALLEL=1` must be set (ADR-0002): put them in `deploy/ollama/ollama.env` of the NFHotel checkout and redeploy it.

```bash
scripts/pull-models.sh
```

Pulls the models of `deploy/models.txt` one at a time and skips those that are installed. It finds the container by its compose labels (project and service `ollama`; `OLLAMA_PROJECT`, `OLLAMA_SERVICE` or `OLLAMA_CONTAINER` name another). It stops with exit code 2 when less than 20 GB is free on the Ollama volume (`MIN_FREE_GB`), and with 3 when no Ollama container answers. `gemma2:9b` is commented out in `deploy/models.txt`: remove the `#` only on a VM with at least 16 GiB memory (ADR-0002).

## Check that it works

```bash
scripts/smoke-test.sh                    # health, 401 without a token, a short run to done
scripts/smoke-test.sh --restart-check    # also: an undelivered result survives a restart
```

The calls run inside the benchmark container. The run uses the first installed model; `--model NAME` picks another. The delivery state at the end is `delivered` when the web API has the result and `pending` while it does not.

## Read a run

Start a run with `POST /runs` and read it with `GET /runs/{id}` (see the OpenAPI file). Results that the web API has not yet accepted are in the volume `results`, folder `pending/`; delivered ones are in `delivered/`, abandoned ones in `failed/`. The file `results.jsonl` in the same volume holds the same rows in the notebook's format.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `deploy.sh` says the network does not exist | Create it once: `docker network create --internal nfhotel-api` |
| `/models` is empty | No model is installed yet, or Ollama is down: `scripts/pull-models.sh` |
| `/models` is slow when Ollama is down | Resolving the name `ollama` takes several seconds; start NFHotel's `ollama` container |
| Start answers 400 `model_not_installed` | The model is not in `ollama list`; pull it |
| Start answers 429 | A run is active and two are waiting; try again after `Retry-After` seconds |
| Delivery stays `pending` | The NFHotel API does not answer; the service retries for 15 minutes after the run ended, then the delivery is `failed` and the file stays in `failed/` |
| Delivery is `failed` at once | The NFHotel API refused the result (400 or 401): check `NFBENCH_WEB_TOKEN` and the contract version |
