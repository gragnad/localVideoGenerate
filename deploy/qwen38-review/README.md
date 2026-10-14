# Qwen3.8 visual reviewer

This replaces the local Qwen3-Omni review server while preserving the old
container, model cache, and reports for rollback. The server remains bound to
`127.0.0.1:8091` and exposes the same OpenAI-compatible model and chat APIs.

The production profile uses the mixed W4A4 `RadixArk/Qwen3.8-27B-NVFP4` checkpoint,
up to two concurrent requests, 64K context, and no audio input. The Personal
Agent allows up to 8K output tokens per model call and automatically continues
an answer when the output limit is reached. Candidate generation on
the Windows lane remains independent; local ComfyUI and this review server are
still mutually exclusive through the existing engine switch.
Multimodal features use CPU transport because Docker's default security profile
does not permit the `pidfd_getfd` operation required by CUDA IPC on this host.
The video engine's own AI review queue and `model-test-review-worker` were retired on
2026-09-27 (archived under `archive/retired_ai_review_20260927/`). This server is now used
only by external clients such as `director-agent`, which reserve it through the
`engine_scheduler` external lease so local H3 generation and Qwen never share the GPU.

Install and create the container:

```bash
./install.sh
docker pull lmsysorg/sglang:qwen38-27b
~/local-ai/review-qwen38/create-container.sh
```

Do not remove `qwen-review-omni-local` until the Qwen3.8 A/B review is accepted.
