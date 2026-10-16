# Methodology

Full text: `BENCHMARK_METHODOLOGY.md` in the repo. Summary:

| Metric | Definition |
|---|---|
| `ttft_s` | first streamed non-empty text (answer or reasoning) minus request start |
| `total_s` | end of stream minus request start |
| `completion_tokens` | server `usage.completion_tokens`; else streamed chunk count (`tokens_estimated = true`) |
| `tokens_per_s` | completion tokens / (end - first token); null if not computable |
| `passed` | deterministic tasks only; hotel analysis has no pass/fail |
| `response_valid` | hotel answer parsed as the required JSON shape; a **format** check, not a quality score |

**Cold vs warm.** The first request per (backend, model) in a session is `cold` and may include model loading. If the model was already loaded it is effectively warm; the flag records position, not a verified load.

**Resources.** Sampled about every 0.25 s: system-wide used RAM (`psutil`) and total GPU memory in use (`nvidia-smi`, summed). These are machine totals, not the model's own footprint. Without an NVIDIA GPU, VRAM is null ("unavailable"), never 0. Peaks can miss spikes shorter than the interval.

**Fairness.** Every model gets the identical prompt and settings; the configuration is stored with each result. Temperature 0 reduces but does not guarantee identical outputs.

**Interpreting.** Speed describes this machine, server version and quantisation. Reasoning models may spend the token budget thinking (`finish_reason = length`) and return no valid answer. Use 3+ runs before comparing close values. There is no automatic "best model".
