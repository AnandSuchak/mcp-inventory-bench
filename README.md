# LASR-MCP: Learned Adaptive Schema Resolution with Dynamic In-Tree Recovery for Enterprise Tool-Calling Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSING.md)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](LICENSING.md)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP Spec: 2026-07-28](https://img.shields.io/badge/MCP%20Spec-2026--07--28-brightgreen.svg)](https://modelcontextprotocol.io/specification)
[![JSON Schema: Draft 2020-12](https://img.shields.io/badge/JSON%20Schema-Draft%202020--12-blueviolet.svg)](https://json-schema.org/draft/2020-12/json-schema-core.html)
[![Tests: 110 Passed](https://img.shields.io/badge/Tests-110%2F110%20Passing-success.svg)](#7-reproducibility--verification)

> **Version:** `2.0.3`<br>
> **Author:** Anand S. Suchak<br>
> **Affiliation:** Independent Researcher | Email: `anand02suchak@gmail.com`<br>
> **Canonical Repository:** [https://github.com/AnandSuchak/mcp-inventory-bench](https://github.com/AnandSuchak/mcp-inventory-bench)<br>
> **Authoritative Manuscript:** [`version_2/paper_v2/main_v2.pdf`](version_2/paper_v2/main_v2.pdf) (15-Page IEEE Conference/Transactions Format)<br>
> **Distribution Bundle:** [`release/v2.0.3/`](release/v2.0.3/) | Pre-packaged in [`zenodo_deposit_v2_0_3/`](zenodo_deposit_v2_0_3/)

---

## 1. Research Overview

Enterprise Autonomous Agents built on the **Model Context Protocol (MCP)** frequently interface with large, deeply constrained JSON Schema declarations. In complex workflows (such as enterprise procurement, multi-depot replenishment, and freight logistics), presenting complete monolithic schemas incurs high prompt token overhead and diminishes inference throughput. Conversely, statically stripping schemas to primitive types leads language models into unconstrained argument hallucinations and validation failures.

**LASR-MCP** introduces a tripartite architecture that resolves this systems dilemma through adaptive, closed-loop schema exposure:

```text
Active Tool Schema at Round t:
C_active^(t) = C_I^*  ∪  Ĉ_T(x)  ∪  C_R^(t)
               │         │          │
               │         │          └─► [Tier 3] Dynamically Recovered Constraints (Validator Intercept)
               │         └────────────► [Tier 2] Proactive Intent-Conditioned Bundle (Task Text)
               └──────────────────────► [Tier 1] Invariant Foundation Floor (Structural Safety)
```

1. **Tier 1 — Invariant Foundation Floor ($C_I^*$):** An empirically derived, intent-agnostic core schema floor ($339$ tokens for enterprise procurement) that provides structural definitions (nested object and array types) to prevent early parsing collapses.
2. **Tier 2 — Proactive Intent-Conditioned Predictor ($\hat{C}_T(x)$):** A lightweight classifier that estimates $k$ task-relevant constraint fragments directly from user task text prior to tool invocation.
3. **Tier 3 — Dynamic In-Tree Recomposition ($C_R^{(t)}$):** A deterministic recovery operator that intercepts pass-level validation diagnostics (RFC 6901 JSON Pointers and violated keywords) upon validation failure and splices only the violated constraints directly into the active JSON Schema tree for subsequent retry attempts.

---

## 2. Research Contributions

- **Adaptive JSON Schema Resolution:** Closed-loop pruning and dynamic expansion of Draft 2020-12 tool schemas tailored to runtime execution needs.
- **Multi-Label Intent-Conditioned Constraint Prediction:** Linguistic and semantic mapping of task prompts to domain constraints without requiring prompt-level schema leakage.
- **Multi-Error Validator Interception:** Extraction of fine-grained error paths from JSON Schema validators for surgical error recovery.
- **Native In-Tree Schema Recomposition:** Deterministic mutation of active schema abstract syntax trees via RFC 6901 JSON Pointers, preserving full dialect compliance.
- **Finite Monotonic Recovery Bound:** Theoretical proof guaranteeing recovery termination within $K \le M - |A_0|$ schema-expansion transitions without non-monotonic schema oscillations.
- **Empirical Retry-Amortization Analysis:** Characterization of the *Retry-Amortization Boundary*, establishing the exact operational conditions under which adaptive pruning outperforms or underperforms monolithic schema delivery.
- **Open-Science Telemetry & Benchmark:** Full raw call ledgers ($7,860$ response-bearing Gemini API invocations, $154$ transport retries, $3,840$ trials) released under open-access terms.

---

## 3. Experimental Setup

The canonical live evaluation reported in manuscript v2.0.3 was conducted under the following pre-specified and audited parameters:

| Parameter | Specification |
| :--- | :--- |
| **Total Completed Trials** | $N = 3,840$ |
| **Unique Evaluation Tasks** | $32$ synthetic enterprise tasks (4 clusters of 8 tasks each) |
| **Experimental Arms** | $6$ distinct arms evaluated symmetrically |
| **Replicates per Task-Arm** | $20$ fixed-seed repeated runs |
| **Model** | `gemini-3.5-flash-lite` |
| **Inference Temperature** | $0.2$ |
| **Execution Seed** | $42$ |
| **Response-Bearing API Calls** | $7,860$ |
| **Client Transport Retries** | $154$ (automatic client-side backoff) |
| **Dialect & Standard** | JSON Schema Draft 2020-12 / Model Context Protocol |

### Experimental Arms

1. **Full Schema Control (`full`):** Static baseline transmitting the complete monolithic tool schema ($552.0$ tokens) upfront on every turn.
2. **Invariant Baseline (`ci_k0`):** Pruned baseline presenting only the invariant floor ($C_I^*$, $339.0$ tokens) without proactive prediction or reactive recovery.
3. **Proactive Static Control (`ci_k1_static`):** Invariant floor augmented with top-$1$ proactive predicted constraints, but no closed-loop retry recovery.
4. **Proactive-Reactive LASR (`ci_k1_reactive`):** Invariant floor + top-$1$ proactive prediction + closed-loop reactive in-tree error recovery.
5. **Proposed LASR (`ci_k2_reactive`):** Invariant floor + top-$2$ proactive prediction + closed-loop reactive in-tree error recovery.
6. **Task-Aware Oracle Reference (`oracle_reactive`):** Theoretical reference exposing the minimal exact constraint bundle required for each specific task.

---

## 4. Empirical Benchmark Results (Table IV)

The table below presents the verified results from the canonical $3,840$-trial live benchmark across all six arms. All token figures reflect provider-reported Prompt-plus-Candidate (P+C) usage from `usageMetadata` ($\text{promptTokenCount} + \text{candidatesTokenCount} = \text{totalTokenCount}$):

| Experimental Arm | Reactive Recovery? | Mean P+C Tokens / Trial | Total P+C Workload | Structural Reliability | Semantic Correctness | Signed Workload Savings vs. Full (95% Bootstrap CI) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Full Schema Control** | No | 1,116.8 | 714,740 | 100.0% | 96.9% | 0.0% (Baseline Reference) |
| **`ci_k0` (Floor Baseline)** | No | 2,057.7 | 1,316,900 | 87.5% | 84.4% | -84.25% ([-125.15%, -49.21%]) |
| **`ci_k1_static`** | No | 1,919.3 | 1,228,340 | 90.6% | 87.5% | -71.86% ([-109.18%, -40.22%]) |
| **`ci_k1_reactive`** | **Yes** | 1,601.4 | 1,024,880 | 96.9% | 93.8% | -43.39% ([-70.15%, -19.70%]) |
| **`ci_k2_reactive` (Proposed)**| **Yes** | **1,406.5** | **900,140** | **96.9%** | **93.8%** | **-25.94% ([-52.55%, -3.16%])** |
| **`oracle_reactive`** | **Yes** | 1,377.8 | 881,820 | 96.9% | 93.8% | -23.38% ([-49.56%, -1.17%]) |

*Note: Signed savings are defined as $(T_{\text{full}} - T_{\text{arm}}) / T_{\text{full}} \times 100$. Negative values indicate higher token workload. Percentile bootstrap intervals (10,000 resamples, seed 42) cluster over task IDs.*

---

### Critical Scientific Findings: The Retry-Amortization Boundary

The empirical benchmark reveals critical systems dynamics that qualify prior preliminary claims:

1. **Proposed LASR vs. Zero-Constraint Floor:** Proposed LASR $k=2$ consumes **$31.65\%$ fewer tokens** than the zero-constraint baseline (`ci_k0`: $900,140$ vs. $1,316,900$ tokens), demonstrating substantial token compression over naive unconstrained generation.
2. **Benchmark-Wide Penalty vs. Full Schema Control:** Across the entire $3,840$-trial benchmark, proposed LASR $k=2$ consumes **$+25.94\%$ MORE tokens** than Full Schema Control ($900,140$ vs. $714,740$ tokens; 95% CI: $[-52.55\%, -3.16\%]$). **LASR does NOT establish overall token savings across heterogeneous benchmark tasks.**
3. **Regime-Dependent Efficiency (Routine Cluster C1):**
   - In **Cluster C1 (`routine_regional_replenish`)**, where proactive prediction accuracy is high and constraint violations are minimal, proposed LASR $k=2$ achieves **$13.49\%$ lower token consumption** than Full Schema Control ($847.6$ vs. $979.8$ tokens/trial) while delivering **$100.0\%$ structural reliability**.
4. **Retry Cascades in Complex Clusters (C2–C4):**
   - In **Cluster C2 (`expedited_emergency_order` / Expedited Emergency Orders)**, LASR incurs $+22.23\%$ higher token spend ($1,557.5$ vs. $1,274.2$ tokens; signed savings: $-22.23\%$).
   - In **Cluster C3 (`specialized_bulk_procurement` / Specialized Bulk Procurement)**, LASR incurs $+59.79\%$ higher token spend ($1,610.9$ vs. $1,008.1$ tokens; signed savings: $-59.79\%$).
   - In **Cluster C4 (`multi_item_depot_rebalance` / Multi-Item Depot Rebalancing)**, LASR incurs $+33.60\%$ higher token spend ($1,609.9$ vs. $1,205.0$ tokens; signed savings: $-33.60\%$).
   - **Mechanism:** In multi-turn tool interaction, re-transmitting previous turns, error diagnostics, and assistant responses on Attempt 2 consumes far more tokens than transmitting a complete monolithic schema upfront on Attempt 1. Pruning is only economically sound when first-pass success is high.

---

## 5. Research Limitations & Ethical Disclosures

To prevent overgeneralization, we explicitly disclose the methodological boundaries of this study:

1. **Single Model Family:** Evaluated exclusively on Google Cloud's `gemini-3.5-flash-lite`. Behavior across open-weight models (e.g., Llama 3) or frontier reasoning models may vary.
2. **Synthetic Benchmark Scope:** Tasks are drawn from an enterprise procurement and inventory domain. Production enterprise schemas may feature higher cardinality or dynamic database-backed constraints.
3. **Evaluation Breadth:** Evaluated across $32$ pre-specified tasks grouped into four structural clusters.
4. **Vocabulary & Constraint Recurrence:** Training and evaluation prompts share an enterprise procurement lexicon with recurring constraint patterns.
5. **Calibration Probe Overlap:** An $8$-task calibration probe (`BLIND-C1-013` ... `BLIND-C4-014`) was utilized during development, as disclosed in Section III-F of the manuscript.
6. **Fixed-Seed Determinism:** Replicates operated at fixed seed $42$ and temperature $0.2$; variance primarily captures prompt-caching and service transport behavior.
7. **Single-Tool Focus:** Evaluates deep constraints on a single primary tool (`create_purchase_order`) rather than multi-tool agent routing.
8. **Transport Scope:** Benchmarked via direct REST API client interaction rather than end-to-end stdio/SSE MCP multiplexing.

---

## 6. Repository Architecture & Experimental Scopes

```text
mcp-inventory-bench/
├── datasets/
│   ├── fresh_live_benchmark_n32/      # [SCOPE 2] Canonical 3,840-trial live benchmark (Authoritative)
│   │   ├── benchmark_call_records.jsonl (22 MB, 7,860 calls, SHA-256: a50bd0f8...)
│   │   ├── benchmark_trial_records.json (9.4 MB, 3,840 trials, SHA-256: 24550314...)
│   │   ├── benchmark_summary.json       (5 KB, SHA-256: cdf05169...)
│   │   └── run_manifest.json            (1.1 KB, SHA-256: 83d36e1b...)
│   ├── frozen_benchmark_n32/          # [SCOPE 1] Historical frozen benchmark (v1.0 single-trial archive)
│   │   └── invariant_optimization_summary.json (SHA-256: 78c2c88e...)
│   └── cross_schema_validation/       # [SCOPE 3] Post-freeze 4-domain structural simulation
│       └── cross_schema_results.json    (SHA-256: b3d57636...)
├── version_2/                         # Canonical Version 2.0.3 analysis, scripts & manuscript
│   ├── paper_v2/                      # 15-Page IEEE camera-ready source and compiled PDF
│   │   ├── main_v2.pdf                (525 KB, SHA-256: 73e1b92e...)
│   │   └── main_v2.tex
│   ├── analyze_fresh_benchmark.py     # 10,000-resample paired cluster bootstrap analysis
│   ├── reconcile_canonical_metrics.py # Read-only canonical integrity verifier
│   └── generate_paper_tables_v2.py    # Deterministic Table I-IV generator
├── release/
│   └── v2.0.3/                        # Formal release documentation & cryptographic manifest
│       ├── MANIFEST.sha256            (Verified SHA-256 manifest of all release artifacts)
│       ├── RELEASE_NOTES.md
│       └── DATA_PROVENANCE.md
├── zenodo_deposit_v2_0_3/             # Pre-assembled Zenodo deposit package
├── paper/                             # Historical Version 1.0 (8-page conference draft, archived)
├── trace/                             # Core LASR-MCP runtime operators (slicer, recomposer, validator)
├── tests/                             # Test suite (74 unit & regression tests)
└── generated_tests/                   # Integration and closed-loop tests (20 tests)
```

---

## 7. Reproducibility & Verification

### A. Environment Installation

Ensure Python 3.11+ is installed. Clone the repository and install dependencies:

```bash
git clone https://github.com/AnandSuchak/mcp-inventory-bench.git
cd mcp-inventory-bench
pip install -r requirements.txt
```

### B. Running the Test Suite (110 Tests Passing)

Execute the comprehensive test suite (including unit tests, schema validators, in-tree recomposers, and verifier regression tests):

```bash
# Run all 110 tests across framework and verifiers
pytest

# Or run the 74 core framework tests specifically:
pytest generated_tests tests
```

### C. Running Read-Only Canonical Metric Reconciliation

Verify that all reported numbers match the underlying canonical telemetry byte-for-byte:

```bash
python version_2/reconcile_canonical_metrics.py --check
# Expected output: [SUCCESS] Pure read-only canonical audit passed! All targets match canonical evidence.
```

### D. Reproducing Statistical Bootstrap Analysis

Re-run the 10,000-iteration paired cluster bootstrap over the 3,840 raw trials:

```bash
python version_2/analyze_fresh_benchmark.py
# Computes primary comparison (LASR k=2 vs Full: -25.94%, 95% CI: [-52.55%, -3.16%])
```

### E. Cryptographic SHA-256 Manifest Verification

Verify all datasets and manuscript bundles against the canonical manifest:

```powershell
python -c "
import hashlib
from pathlib import Path
manifest = Path('release/v2.0.3/MANIFEST.sha256')
with open(manifest) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'): continue
        h, p = line.split(maxsplit=1)
        path = Path(p.strip())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == h
        print(f'VERIFIED: {path.name}')
"
```

---

## 8. Publication Details & Citation

- **Author:** Anand S. Suchak
- **Affiliation:** Independent Researcher
- **Manuscript Version:** v2.0.3 (November 2026)
- **Preprint Archive:** Zenodo Open-Science Repository (Deposit package prepared in [`zenodo_deposit_v2_0_3/`](zenodo_deposit_v2_0_3/))

```bibtex
@article{suchak2026lasr_mcp,
  title={{LASR-MCP: Learned Adaptive Schema Resolution with Dynamic In-Tree Recovery for Enterprise Tool-Calling Agents}},
  author={Suchak, Anand S.},
  journal={Open-Science Research Preprint (Zenodo)},
  year={2026},
  version={2.0.3},
  url={https://github.com/AnandSuchak/mcp-inventory-bench}
}
```

---

## 9. License

This repository uses dual open-access licensing (see [`LICENSING.md`](LICENSING.md) for full details):
- **Software & Benchmark Scripts:** [MIT License](LICENSING.md).
- **Academic Manuscript & Research Documentation:** [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSING.md).
- **Benchmark Telemetry & Datasets:** [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSING.md).
