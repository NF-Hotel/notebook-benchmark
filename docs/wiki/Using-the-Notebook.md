# Using the Notebook

1. **Environment / backend status** – connectivity and model count per backend.
2. **Dataset selection** – pick a CSV below `data/` or paste a path; edit the column mapping. Errors (missing file, invalid or empty CSV, missing columns, unrecognised cancellation values) appear as messages.
3. **Model selection** – one or more models per available backend.
4. **Benchmark configuration** – temperature (0), max output tokens (8192), runs per model (1), hotel analysis and/or deterministic tasks. Press **Run benchmark**.
5. **Dataset overview** – file, rows, columns, SHA-256 prefix, types, missing values, sample.
6. **Benchmark execution** – progress and a summary; each request is appended to `output/results.jsonl` immediately.
7. **Performance results** – TTFT, total time, tokens, tokens/s, cold vs warm. Choose the result set (session) and workload.
8. **Hotel cancellation analysis** – Python-calculated overall / direct / agent rates and breakdowns.
9. **LLM analysis comparison** – metrics table and model responses side by side next to the calculated values.
10. **Resource usage** – system RAM and GPU VRAM before / after / peak.
11. **Raw results** – every row of the selection.
12. **Export** – CSV or JSON of the current selection.

The pass/fail heatmap for the deterministic tasks appears under section 7 when they were run.
