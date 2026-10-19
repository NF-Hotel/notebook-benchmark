# Prove it in the VM

The runbook and the checklist of MIL-004: deploy the benchmark service beside the NFHotel services in the Proxmox VM, run the models from the back office, and prove the chain. **Nothing here has been run.** The commands are for the VM, in the order of the steps; the table in "Checklist" is filled in during the run and copied to the wiki afterwards (task 4).

## 1. What only a person with access can do

| Step | Why only you |
| --- | --- |
| Merge the pull requests (notebook-benchmark #6 to #9, NFHotel #116, #151, #152) in their order, or choose which branch the VM runs | A reviewer merges; the AI does not |
| Log in to the Proxmox node and the VM (`PVE_SSH` in `deploy.env`, key login) | The credentials are yours (S03) |
| Say whether the VM has a GPU and whether 12 GiB is the real memory | Decides the model list (ADR-0002) |
| Set `OLLAMA_MAX_LOADED_MODELS=1` and `OLLAMA_NUM_PARALLEL=1` in NFHotel's `deploy/ollama/ollama.env` and redeploy that Ollama | It changes the shared model server |
| Create the two tokens and put them in the git-ignored env files on the VM | Secrets never go in git or in chat |
| Trust the self-signed certificate in a browser (or use a real one), and sign in as a Manager | A person in a browser |
| Create a Receptionist and a Housekeeping account for the 403 check | Needs the API container and a password |
| Stop and start the NFHotel API during a run (the resilience check) | A deliberate outage on a shared VM (S03) |

## 2. Two conflicts with the old setup, and how they were settled

The VM already runs services of the old setup (`NF-Hotel/NFHotel`, `deploy/`). Two findings were made and are fixed in this repository (ADR-0004); this section says what to check.

| Finding | What was done | What to check on the VM |
| --- | --- | --- |
| NFHotel's `deploy/benchmark/docker-compose.yml` (the old marimo notebook) and this repository both used the compose project `benchmark`, a service `benchmark` and a volume `results`. Starting the new file would have replaced the old container and reused its volume | The compose project is now `nfbench` | `docker ps -a --format '{{.Names}}' \| grep -i benchmark` shows the old container (if it runs) and, after the deploy, `nfbench-benchmark-1`; the old one is still running |
| The VM already has an Ollama (`deploy/ollama`, network `nfhotel-llm`) that the market analysis uses. A second Ollama would have cost memory and a second copy of every model on 12 GiB | This repository starts no Ollama. The service joins `nfhotel-llm` and uses `http://ollama:11434`; `scripts/pull-models.sh` pulls into NFHotel's Ollama container | The container exists: `docker ps --filter label=com.docker.compose.project=ollama --filter label=com.docker.compose.service=ollama`. Set `OLLAMA_MAX_LOADED_MODELS=1` and `OLLAMA_NUM_PARALLEL=1` in `/opt/nfhotel/deploy/ollama/ollama.env` (the example file there does not have them yet) and redeploy it |

Consequence: the market analysis and the benchmark share one model server, so a benchmark run slows an analysis that runs at the same moment. Do not run both during the proof.

## 3. What the VM needs (pre-flight)

Run on the VM and write the answers in the record. Stop if a line fails.

| # | Need | Command | Wanted |
| --- | --- | --- | --- |
| 1 | Docker and compose v2 | `docker --version && docker compose version` | Compose v2 with `--wait` |
| 2 | Memory | `free -m` | Total 12288 MiB or more; at least 8 GiB free while the web application, API and PostgreSQL run |
| 3 | Disk | `df -h /var/lib/docker` | At least 25 GB free (about 15 GB of models, the images, the volumes); the pull script stops below 20 GB |
| 4 | CPU and GPU | `nproc; lspci \| grep -i -E 'nvidia\|vga'` | Write down both; no GPU is a valid run and is named in the result |
| 5 | The internal network of the web and the API | `docker network inspect nfhotel-api --format '{{.Internal}}'` | `true` (it is made by `scripts/deploy-services.sh`) |
| 6 | The NFHotel services are up | `docker ps --format '{{.Names}}\t{{.Status}}'` | web, API, PostgreSQL and nginx healthy |
| 7 | The API has the new tables | `docker compose -f /opt/nfhotel/deploy/postgres/docker-compose.yml --env-file /opt/nfhotel/deploy/postgres/postgres.env exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt benchmark_*"'` | `benchmark_run` and `benchmark_result` (migration `AddBenchmarkRun`, applied when the API starts with `Database__MigrateOnStart=true`) |
| 8 | Outbound internet from the Ollama container | `docker exec $(docker ps -q --filter label=com.docker.compose.project=ollama --filter label=com.docker.compose.service=ollama) ollama list` and, for the download, `docker run --rm --network nfhotel-llm curlimages/curl -sI https://registry.ollama.ai \| head -1` | A model list, and an HTTP status line |
| 9 | The Docker network of the Ollama | `docker network inspect nfhotel-llm --format '{{.Internal}}'` | `false` (it must be able to download models) |
| 10 | Which services share names | `docker ps -a --format '{{.Names}}' \| grep -i -E 'benchmark\|ollama'` | Write down what runs; see section 2 |

## 4. The two tokens

Make both on the VM; never paste them into chat or git.

```bash
openssl rand -hex 32    # token 1: the web application calls the benchmark service
```

| Token | Written in | As | Must equal |
| --- | --- | --- | --- |
| 1 | `deploy/benchmark.env` of this repository | `NFBENCH_API_TOKEN` | `BenchmarkService__Token` in `/opt/nfhotel/deploy/nfhotel-web/nfhotel-web.env` |
| 2 (exists) | `Api__Token` in `/opt/nfhotel/deploy/nfhotel-api/nfhotel-api.env` | `NFBENCH_WEB_TOKEN` in `deploy/benchmark.env` | The service token of the NFHotel API (ADR-0004) |

`NFBENCH_WEB_URL` stays `http://nfhotel-api:8080`. `NFBENCH_OLLAMA_URL` stays `http://ollama:11434`, the Ollama of NFHotel.

## 5. Steps

All on the VM unless it says workstation.

### 5.1 NFHotel side

1. Merge the NFHotel pull requests, then update the checkout: `cd /opt/nfhotel && git pull`.
2. Set `BenchmarkService__Token` in `deploy/nfhotel-web/nfhotel-web.env` (token 1).
3. From the workstation: `bash scripts/deploy.sh api web` (builds the API and the web application; the API applies the migration on start).
4. Check the tables again (pre-flight line 7) and that `https://<vm>/admin/benchmark` opens for a Manager and shows the empty list.

### 5.2 Benchmark side

1. `git clone https://github.com/NF-Hotel/notebook-benchmark.git /opt/notebook-benchmark && cd /opt/notebook-benchmark` (the branch after the merges).
2. Do the check of section 2 for the Ollama settings (`OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`).
3. `cp deploy/benchmark.env.example deploy/benchmark.env`; fill in token 1 and token 2.
4. `scripts/deploy.sh`: checks the two networks, builds the image and waits for the container to be healthy. It refuses to start while a token is empty or `change-me`.
5. `scripts/pull-models.sh`: pulls the models of `deploy/models.txt` one at a time into NFHotel's Ollama. Expect the first pull to take a long time. If less than 20 GB is free it stops with exit code 2 and pulls nothing.
6. `scripts/smoke-test.sh`: health, 401 without a token, and one short run to `done`. With the NFHotel API up it ends with `delivery: delivered`.

### 5.3 The full run from the back office

1. Open `https://<vm>/admin/login` and sign in as a Manager.
2. Open `/admin/benchmark/start`, choose the models, keep the hotel analysis, start the run.
3. Watch the state (queued, running, done) and the result (waiting to be stored, stored). Note the start and end time.
4. Open `/admin/benchmark`: the run is in the list. Open it and compare one model's figures with the result file (check 2).

## 6. Checklist

Fill in during the run. Criteria are those of MIL-004.

| # | Criterion | How | Wanted | Result |
| --- | --- | --- | --- | --- |
| 1 | A run started by a Manager reaches `done` and is listed with every chosen model | Section 5.3, steps 2 to 4 | The list shows every model | |
| 2 | The measurements in the page equal the result file | In the VM: `docker compose -f /opt/notebook-benchmark/deploy/docker-compose.yml --env-file /opt/notebook-benchmark/deploy/benchmark.env exec -T benchmark tail -n 3 /data/results.jsonl`; compare `total_s`, `completion_tokens`, `tokens_per_s` of one request with the detail page | Equal (the page rounds to two decimals) | |
| 3 | Resilience: delivery after an outage, exactly one row | See 6.1 | Delivered within 15 minutes of the restart; one `benchmark_run` row for the run id | |
| 4a | A Receptionist gets 403 | Sign in as a Receptionist; open `/admin/benchmark` and `/admin/benchmark/start` | The page says access is not permitted | |
| 4b | A Housekeeping user gets 403 | The same as Housekeeping | The same | |
| 4c | The benchmark API without the token gets 401 | `scripts/smoke-test.sh` (its first checks) | `ok   start without a token gets 401` | |
| 5 | No published host port; only 80 and 443 answer from outside | In the VM: `docker inspect -f '{{.Name}} {{json .NetworkSettings.Ports}}' $(docker ps -q) \| grep -i -E 'benchmark\|ollama'` (the NFHotel Ollama and the new benchmark container); from the workstation: a port scan of the VM address | `{}` for both containers; only 80 and 443 open | |
| 6 | The wiki page names the models, the machine, the times and the commands | Task 4 | The page exists in the benchmark wiki | |

### 6.1 The resilience check

This is a deliberate short outage of the NFHotel API, the service that stores results. Do it in a quiet moment.

1. Start a run from the back office (one small model, one run).
2. While it is `running`, stop the API: `cd /opt/nfhotel && docker compose -f deploy/nfhotel-api/docker-compose.yml --env-file deploy/nfhotel-api/nfhotel-api.env stop` (set `API_TOKEN` as the deploy script does if compose asks for it).
3. Wait for the run to be `done`. Read the delivery state through the benchmark service: it stays `pending`, and `pending/<run id>.json` is in the volume.
4. Start the API again (`up -d`). The benchmark service retries after 5 seconds, then 10, doubling; the result must be delivered within 15 minutes of the run ending, and the page shows the run once.
5. Count the rows: the same `psql` command as pre-flight line 7 with `select count(*) from benchmark_run where run_id = '<run id>';` must give 1.
6. Optional: `scripts/smoke-test.sh --restart-check` (needs the API stopped) checks that a pending result survives a restart of the benchmark container.

If the outage lasts longer than 15 minutes the delivery becomes `failed` and the file moves to `failed/`; that is the specified behaviour, and the result can be sent by hand (not automated).

## 7. Stop and roll back

| Situation | Action |
| --- | --- |
| Memory runs out or the VM swaps | `docker compose -f deploy/docker-compose.yml --env-file deploy/benchmark.env down` in the benchmark checkout (the volume is kept); drop `qwen2.5:7b` from `deploy/models.txt`; ADR-0002 says the list is a new version of the record |
| The new tables are missing | Check `Database__MigrateOnStart` and the API log; do not create tables by hand |
| A token mismatch (401 on start, or delivery `failed` at once) | Compare token 1 and token 2 as in section 4; the benchmark log says that the web API rejected the run, and never prints a token |
| The old notebook stopped | It should not: the project is now `nfbench`. If it did, restore it with `scripts/deploy-services.sh benchmark` in `/opt/nfhotel` and report it |

## 8. Record of the run

Copy this into the wiki page of task 4 after the run.

| Item | Value |
| --- | --- |
| Date and who | |
| VM: memory, cores, GPU, disk free | |
| Versions: Docker, Compose, Ollama, the two repositories (commit) | |
| Models and the size of each (`ollama list`) | |
| Run id, start, end | |
| Time per model (cold and warm) | |
| Delivery: delivered at, after how long | |
| Checklist results 1 to 6 | |
| Deviations and what was changed | |
