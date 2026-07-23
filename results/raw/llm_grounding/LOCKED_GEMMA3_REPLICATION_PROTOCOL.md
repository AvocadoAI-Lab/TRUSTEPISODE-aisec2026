# Locked Gemma3 replication protocol

- Frozen at: `2026-07-23T15:50:17Z`
- Status at freeze: the Qwen2.5-7B held-out result had already been observed; Gemma3 had not
  been downloaded or queried on any development or held-out card.
- Rationale: `gemma3:1b` is the default edge model in the deployed investigation configuration.
  This replication tests whether the same typed AuditRecord interface transfers to that
  deployment-relevant smaller model. It is not a preregistered model comparison.

## Locked execution

- Model tag: `gemma3:1b`
- Endpoint: local Ollama native `/api/chat`
- Runs: exactly one pass over H01--H20
- Temperature: `0`
- Seed: `20260723`
- Maximum generated tokens: `192`
- System prompt SHA-256:
  `65c474d69c5e01bed70074cd513578edcdb5de0eb78c472ed4590e30743e8c11`
- Response schema SHA-256:
  `sha256:a935c73a17f66ceeb00e27c6d941ec9eb7479aa9fc56391192518f3eefcbea30`
- Cards SHA-256:
  `sha256:add0d65c934cec2574bc353216bb3b858bfa892bbc0882b372b99a724edf11d6`
- Records SHA-256:
  `sha256:1c5f4f088268739d1eb48835fe33e3235be2dfae0f87cffbf617f9da85fd0b84`

No prompt, card, expected answer, citation set, or scoring rule may change after model download.
The model digest returned by Ollama, all raw responses, failures, token counts, and aggregate
metrics must be retained regardless of outcome. The existing Qwen result must not be re-run or
overwritten.
