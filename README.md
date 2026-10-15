# LASR-MCP: Learned Adaptive Schema Resolution with Dynamic In-Tree Recovery for Enterprise Tool-Calling Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP Spec: 2026-07-28](https://img.shields.io/badge/MCP%20Spec-2026--07--28-brightgreen.svg)](https://modelcontextprotocol.io/specification)
[![JSON Schema: Draft 2020-12](https://img.shields.io/badge/JSON%20Schema-Draft%202020--12-blueviolet.svg)](https://json-schema.org/draft/2020-12/json-schema-core.html)
[![Tests: 74 Passed](https://img.shields.io/badge/Tests-74%2F74%20Passing-success.svg)](#reproducibility-verification)

> **Author**: Anand S. Suchak  
> *Independent Systems Researcher* | Email: `anand02suchak@gmail.com`  
> **Canonical Repository**: [https://github.com/AnandSuchak/mcp-inventory-bench](https://github.com/AnandSuchak/mcp-inventory-bench)  
> **Camera-Ready Artifact**: `release_archive/lasr_mcp_camera_ready_package.zip` (SHA-256 Manifest Verified)

---

## 1. Executive Summary

As enterprise computing transitions toward autonomous agentic workflows, the **Model Context Protocol (MCP)** has emerged as the open standard interface for tool discovery and parameter integration. However, exposing complex enterprise contracts (such as multi-constraint procurement, logistics, and inventory dispatching) presents a fundamental systems dilemma:
- **The Monolithic Full-Schema Tax**: Transmitting complete monolithic schemas (frequently exceeding 500–650 tokens per tool) on every turn inflates prompt token overhead, drives up operational API costs, and degrades inference throughput.
- **The Brittleness of Naive Truncation**: Statically stripping schemas down to basic primitive types eliminates critical domain constraints (e.g., regex patterns, enum bounds, item limits), causing language models to hallucinate invalid arguments and suffer catastrophic validation failures.

**LASR-MCP** resolves this trade-off through a tripartite architectural framework:
1. **Tier 1 — Invariant Foundation Floor ($C_I^*$):** An empirically selected minimal constraint subset ($339$ tokens for procurement) that establishes a baseline structural viability floor without intent conditioning.
2. **Tier 2 — Proactive Intent-Conditioned Predictor ($\hat{C}_T(x)$):** A lightweight semantic classifier that predicts task-relevant constraint bundles from user intent prior to tool invocation.
3. **Tier 3 — Dynamic In-Tree Recomposition ($C_R^{(t)}$):** A closed-loop reactive operator that intercepts pass-level multi-error validator diagnostics (RFC 6901 JSON Pointers and keywords) and splices canonical constraint nodes directly into the native JSON Schema tree on Attempt 2.

```text
Active Tool Schema at Round t:
C_active^(t) = C_I^*  ∪  Ĉ_T(x)  ∪  C_R^(t)
               │         │          │
               │         │          └─► [Tier 3] Dynamically Recovered Constraints (Validator Intercept)
               │         └────────────► [Tier 2] Proactive Intent-Predicted Bundle (Task Text)
               └──────────────────────► [Tier 1] Invariant Foundation Floor (Structural Safety)
```

---

## 2. Cryptographic Manifests & Data Provenance

All experimental data, recorded execution traces, and benchmark harnesses are immutably archived with automated SHA-256 cryptographic manifests:

### A. Primary Frozen Benchmark ($N=32$ Tasks, 4 Operational Archetypes)
- **Git Commit Hash**: `9807340abc38170e0090a102547ee4309c01d78b`
- **Data File**: [`datasets/frozen_benchmark_n32/invariant_optimization_summary.json`](datasets/frozen_benchmark_n32/invariant_optimization_summary.json)
- **SHA-256 Digest**:
  ```text
  78c2c88ed5128e0f296fa29e0c258589b516f3adb14b0b8da491fa73bc3ffc11
  ```

### B. Post-Freeze Cross-Schema Robustness Study ($N=32$ Tasks, 4 Enterprise Domains)
- **Data File**: [`datasets/cross_schema_validation/cross_schema_results.json`](datasets/cross_schema_validation/cross_schema_results.json)
- **SHA-256 Digest**:
  ```text
  b3d57636f9834ff536204acfe88454c9620228bb67705f1b3caa40e0d562302a
  ```

---

## 3. Empirical Evaluation & Benchmark Results

### Table I: Full-Spectrum Systems Evaluation (32-Task Development/Validation Benchmark)
*Evaluated on Google Cloud `gemini-3.5-flash-lite` with provider-reported `totalTokenCount` accounting.*

| System Arm | Reactive? | Init $S_0$ (tok) | Exp. $\Delta S$ (tok) | 1st-Pass Struct. | Final Struct. | Semantic Corr. | Mean $TTS$ | Total Workload Tokens | Token Reduction |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Full Schema Control** | No | 552.0 | 0.0 | 31.2% | 93.8% | 90.6% | 2913.2 | 96,629 | baseline |
| **$C_I^*$ Baseline ($k=0$)** | No | 339.0 | 0.0 | 0.0% | 68.8% | 65.6% | 3182.9 | 102,407 | +6.0% (overhead) |
| **LASR $k=1$ (Static)** | No | 361.1 | 0.0 | 15.6% | 78.1% | 71.9% | 2410.6 | 83,754 | -13.3% |
| **LASR $k=1$ (Reactive)** | **Yes** | 361.1 | 45.4 | 15.6% | **100.0%** | **93.8%** | 2410.6 | **77,140** | **-20.2%** |
| **LASR $k=2$ (Reactive)** | **Yes** | 366.8 | 43.8 | 18.8% | **100.0%** | **93.8%** | **2351.5** | **75,248** | **-22.1%** |
| **Oracle $O(x)$ (Reactive)\*** | Yes | 359.0 | 48.3 | 15.6% | 96.9% | 93.8% | 2325.3 | 75,649 | -21.7% |

*\*Note: Oracle $O(x)$ is a model-conditional reference baseline constructed from task specifications. Mean $TTS$ is conditional on successful trajectories ($N_{\text{succ}}$); Total Tokens sums all turns across all 32 tasks.*

---

### Table IV: Cross-Schema Robustness Evaluation across 4 Enterprise Domains
*Stress-testing architectural transfer across four heterogeneous synthetic contracts ($N=32$ tasks total, 8 per domain; 50/50 explicit vs. ambiguous split).*

| Enterprise Tool Schema | Domain / Key Constraints | Init $S_0$ | Full $S$ | Token Savings | 1st-Pass (Exp/Amb) | Final Struct. | Semantic Corr. | Ambiguous Task Recovery |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `create_purchase_order` | Procurement (Regex, enums, budget bounds) | 339 | 552 | **21.3%** | 50.0% (4/4, 0/4) | **100.0%** | 87.5% | **100.0% (4/4)** |
| `inventory_adjustment` | Warehouse Stock (Signed deltas, facility codes) | 299 | 541 | **22.4%** | 50.0% (4/4, 0/4) | **100.0%** | 87.5% | **100.0% (4/4)** |
| `shipment_creation` | Freight Logistics (Nested packages, tracking regex) | 337 | 646 | **25.2%** | 50.0% (4/4, 0/4) | **100.0%** | 100.0% | **100.0% (4/4)** |
| `customer_refund` | Financial Accounting (Refund limits, currency enums) | 292 | 474 | **20.5%** | 50.0% (4/4, 0/4) | **100.0%** | 100.0% | **100.0% (4/4)** |
| **Macro Mean / Aggregate** | **Cross-Domain Summary ($N=32$)** | **316.8** | **553.2** | **22.5%** | **50.0% (16/16, 0/16)** | **100.0%** | **93.8%** | **100.0% (16/16)** |

---

## 4. Key Empirical Takeaways

1. **Semantic Predictability ($H_1$)**: Task text contains strong predictive signals for intent-conditioned rules. On unseen syntactic template families, LASR achieves $F_1 = 0.863$ versus $0.250$ for frequency baselines ($\Delta F_1 = +0.612, p < 0.001$).
2. **Invariant Safety Floor ($H_2$)**: Operating below the empirical floor ($339$ tokens) causes structural validity to collapse from $75.0\%$ to $50.0\%$ on the calibration probe due to missing nested container definitions.
3. **Causal Contribution of Reactive Recovery ($H_3$)**: Paired comparison against static adaptive exposure demonstrates a $+21.9\text{ pp}$ gain in structural validity ($78.1\% \rightarrow 100.0\%$, exact one-sided McNemar test $p = 0.0078125$), successfully recovering all $27/27$ initially failed trajectories within 3 attempts.
4. **Workload Token Economics ($H_4$)**: Rather than increasing token spend through retries, reactive LASR saves $6,614$ tokens ($-7.9\%$) over static LASR and $21,381$ tokens ($-22.1\%$) over Full Schema by resolving errors on Attempt 2 and terminating retry cascades early.

---

## 5. Repository Structure

```text
mcp-inventory-bench/
├── datasets/
│   ├── frozen_benchmark_n32/          # Primary frozen benchmark dataset & cryptographic manifest
│   │   ├── invariant_optimization_summary.json  (SHA-256: 78c2c88e...)
│   │   └── MANIFEST.sha256
│   └── cross_schema_validation/       # 4-domain cross-schema robustness dataset & manifest
│       ├── cross_schema_results.json            (SHA-256: b3d57636...)
│       └── MANIFEST.sha256
├── paper/                             # IEEE conference publication source files
│   ├── main.tex                       # Primary LaTeX driver (Exact 8-page format)
│   ├── sections/                      # Section-by-section LaTeX modules (00 to 07)
│   ├── tables/                        # Tables I through IV
│   ├── references.bib                 # Cleaned bibliography (Sadani, Cho, Zhai, Sakizli, etc.)
│   └── main.pdf                       # Compiled camera-ready PDF (Exact 8 pages, 27 embedded fonts)
├── release_archive/                   # Release bundle for camera-ready distribution
│   ├── main.pdf                       # Canonical camera-ready PDF
│   ├── lasr_mcp_camera_ready_package.zip  # Self-contained submission archive
│   ├── RELEASE_MANIFEST.sha256        # Comprehensive bundle checksums
│   └── RELEASE_METADATA.json          # Machine-readable provenance metadata
├── tests/                             # Comprehensive 74-test regression test suite
│   ├── test_frozen_integrity.py       # Cryptographic manifest & dataset immutability tests
│   ├── test_cross_schema.py           # Multi-domain transfer & recovery verification
│   ├── test_token_accounting.py       # Gemini API totalTokenCount decomposition tests
│   ├── test_recomposer.py             # JSON Pointer in-tree recomposition tests
│   ├── test_validator.py              # JSON Schema Draft 2020-12 validator tests
│   └── test_predictor.py              # Linear intent classifier tests
├── trace/                             # Core LASR-MCP runtime operators
│   ├── recomposer.py                  # In-tree JSON Schema tree recomposition operator
│   ├── validator.py                   # Draft 2020-12 multi-error diagnostic extractor
│   └── slicer.py                      # Invariant foundation extractor & serializer
└── requirements.txt                   # Frozen Python environment dependencies
```

---

## 6. Reproducibility & Build Verification

### Environment Setup
```bash
# Clone the canonical repository
git clone https://github.com/AnandSuchak/mcp-inventory-bench.git
cd mcp-inventory-bench

# Create and activate Python virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run Full Regression Suite (74/74 Passing)
```bash
pytest -q
# Expected output: 74 passed in ~0.50s
```

### Verify Cryptographic Dataset Checksums
```bash
# Verify primary frozen benchmark (commit 9807340)
certutil -hashfile datasets/frozen_benchmark_n32/invariant_optimization_summary.json SHA256
# Expected: 78c2c88ed5128e0f296fa29e0c258589b516f3adb14b0b8da491fa73bc3ffc11

# Verify cross-schema robustness dataset
certutil -hashfile datasets/cross_schema_validation/cross_schema_results.json SHA256
# Expected: b3d57636f9834ff536204acfe88454c9620228bb67705f1b3caa40e0d562302a
```

### Deterministic PDF Compilation
```bash
# Uses Tectonic engine with fixed timestamp for bit-for-bit reproducibility
$env:SOURCE_DATE_EPOCH = "1725969600"
.\bin\tectonic.exe -Z search-path=paper paper\main.tex
# Result: Exactly 8 pages, 27/27 fonts embedded, zero undefined markers
```

---

## 7. Citation

If you use this benchmark dataset, runtime framework, or cite the empirical findings in your research:

```bibtex
@article{suchak2026lasr_mcp,
  title={{LASR-MCP: Learned Adaptive Schema Resolution with Dynamic In-Tree Recovery for Enterprise Tool-Calling Agents}},
  author={Suchak, Anand S.},
  journal={Open-Science Research Preprint (Zenodo)},
  year={2026},
  url={https://github.com/AnandSuchak/mcp-inventory-bench}
}
```

---

## 8. License

This project is licensed under the [MIT License](LICENSE). All benchmark data, schemas, and execution traces are open for academic and commercial research under open-science principles.
