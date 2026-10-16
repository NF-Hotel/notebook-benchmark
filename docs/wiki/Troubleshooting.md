# Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Backend shows UNAVAILABLE | Start the server, press *Re-check backends*. LM Studio: enable the local server on port 1234. |
| Answer marked invalid, `finish_reason = length` | The token budget ran out (common with reasoning models). Raise *Max output tokens*. |
| First request is very slow | Model loading (cold). Compare warm runs for latency. |
| VRAM "unavailable" | No NVIDIA GPU, or `nvidia-smi` is not on PATH. |
| Dataset error: required column not found | Fix the column mapping in section 2. |
| Valid JSON but odd content | Valid means format only; read the response next to the calculated values. |
