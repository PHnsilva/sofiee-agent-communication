# Candidate local model for Communication

This is a measured prototype candidate, not an approved production model or a quality baseline.

## Candidate and license

- Candidate: Qwen2.5-Coder-1.5B-Instruct, Q4_K_M GGUF via Ollama.
- Local Ollama tag observed: hf.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF:Q4_K_M.
- Publisher model card and license: [Qwen2.5-Coder-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct), Apache-2.0.
- Runtime: Ollama 0.40.14 on CPython 3.13.15 host; server bound to 127.0.0.1, cloud disabled; model and temporary files under C:\DevData\Codex\agents\local-inference\2026-11-09.
- No model was downloaded or installed during this issue.

## Measurement on 2026-11-10

Synthetic requests used no personal or private examples. CPU inference returned JSON for intent/extraction tasks in 1.5–8.2 seconds after startup. It correctly extracted a simple arithmetic operation, kept the four required product filters without naming a site, and returned inconclusive when a study claim had no source details. These are smoke observations, not accuracy measurements.

A summarization request preserved the date and closure time but changed “Friday” to “the weekend.” This is a material meaning error. The candidate is therefore opt-in only and needs human review; the measurement does not establish adequate general communication quality. No baseline or improvement claim is made.

## Runtime policy

The code uses the candidate only when SOFIEE_AGENT_LOCAL_MODEL is explicitly set. The adapter is fixed to loopback, limits the prompt, context, output tokens, concurrent requests, and timeout, and unloads the model after a call. A missing model, timeout, malformed output, or cancellation returns a structured error; no response is fabricated and no remote fallback is available.

Ollama process memory is not enforceable from this client. The service must be started with OLLAMA_NO_CLOUD=1, OLLAMA_HOST=127.0.0.1:11434, and model/cache/temp paths on C:. Cancellation suppresses the result and is bounded by the configured socket timeout; the runtime cannot forcibly interrupt an in-flight Ollama computation.
