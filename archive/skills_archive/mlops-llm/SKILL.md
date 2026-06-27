---
name: mlops-llm
description: "Umbrella skill for LLM inference, serving, alignment, and fine-tuning (TRL, Unsloth, vLLM)."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [mlops, llm, inference, training, fine-tuning, serving, alignment]
---

# LLM Operations (Inference & Training)

This umbrella skill captures advanced patterns for the entire LLM lifecycle—from training and alignment to high-performance serving.

## 1. Inference & Serving
- **vLLM**: High-throughput serving via OpenAI-compatible API.
- **llama.cpp**: Local GGUF inference and model discovery.
- **Quantization**: Multi-backend quantization support (GPTQ, AWQ, GGUF).

## 2. Training & Fine-tuning
- **Frameworks**: TRL, Unsloth, and HuggingFace Transformers.
- **Experiment Tracking**: **Weights & Biases** (W&B) for logging sweeps and model registry.

## 3. Evaluation & Alignment
- **Benchmarks**: **lm-eval-harness** for MMLU, GSM8K, and custom tasks.
- **Refusal Abliteration**: **OBLITERATUS** logic for diff-in-means refusal removal.

## 4. Hub Operations
- **HuggingFace CLI**: Search, download, and upload models/datasets.

## Common Pitfalls
- **Tokenizer Mismatch**: Ensure the structured generation tokenizer matches the model's native tokenizer.
- **VRAM Fragmentation**: Monitor PagedAttention block usage in vLLM to prevent OOM.
- **Alignment Drift**: Cross-verify DPO results against base model benchmarks to ensure reasoning hasn't degraded.
