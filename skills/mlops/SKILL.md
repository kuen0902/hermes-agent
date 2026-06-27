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

# Machine Learning Operations (MLOps) & Data Infrastructure

This umbrella skill governs advanced patterns for managing the ML lifecycle, focusing on data foundations, LLM alignment, and high-throughput serving.

## 1. Data Engineering & Pipeline Integrity
- **Orchestration**: Managing ETL flows and pipeline triggers. See `data-engineering` references for DuckDB/Postgres patterns.
- **Exploration**: Interactive data discovery, visualization, and DuckDB analytics.
- **Quality**: Automated checks for data drift, NaNs, and schema validation.

## 2. Inference & High-Performance Serving
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
