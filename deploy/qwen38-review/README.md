# Qwen3.8 visual reviewer

This replaces the local Qwen3-Omni review server while preserving the old
container, model cache, and reports for rollback. The server remains bound to
`127.0.0.1:8091` and exposes the same OpenAI-compatible model and chat APIs.

The initial production profile uses the BF16 `Qwen/Qwen3.8-27B` checkpoint,
one request at a time, 32K context, and no audio input. Candidate generation on
the Windows lane remains independent; local ComfyUI and this review server are
still mutually exclusive through the existing engine switch.
Multimodal features use CPU transport because Docker's default security profile
does not permit the `pidfd_getfd` operation required by CUDA IPC on this host.
The installer adds a later systemd environment file for the review worker, so
the existing `runtime.env` and its Omni rollback values stay untouched.
Qwen's internal thinking mode is disabled for this continuous queue: the worker
already uses two review passes, while dense-27B thinking made each candidate
take tens of minutes on the DGX Spark.

Install and create the container:

```bash
./install.sh
docker pull lmsysorg/sglang:qwen38-27b
~/local-ai/review-qwen38/create-container.sh
```

Do not remove `qwen-review-omni-local` until the Qwen3.8 A/B review is accepted.
