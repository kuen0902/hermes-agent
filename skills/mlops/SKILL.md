---
name: mlops
description: Umbrella skill for the entire machine learning lifecycle—from data and training to evaluation and high-performance serving.
category: mlops
version: 1.0.0
author: Hermes (Curator)
license: MIT
metadata:
  hermes:
    tags: [mlops, llm, inference, fine-tuning, training, serving, evaluation]
---

# Machine Learning Operations (MLOps)

This umbrella skill governs advanced patterns for managing the ML lifecycle, focusing on LLM alignment, high-throughput serving, and robust experiment tracking.

## 1. Inference & High-Performance Serving
- **vLLM**: Serving via OpenAI-compatible APIs.
- **llama.cpp**: GGUF discovery and local inference.
- **Quantization**: Managing GPTQ, AWQ, and GGUF backends.

## 2. Training, Fine-Tuning & Alignment
- **Frameworks**: TRL, Unsloth, and Transformers for SFT and DPO.
- **Alignment**: Techniques like Refusal Abliteration (OBLITERATUS).
- **Tracking**: Using Weights & Biases (W&B) for sweeps and registries.

## 3. Evaluation & Data Operations
- **Benchmarks**: Using `lm-eval-harness` for standard and custom metrics.
- **Hub Ops**: Leveraging HuggingFace CLI for model/dataset management.
- **Data Prep**: Handling specific dataset formats for training and RL.
