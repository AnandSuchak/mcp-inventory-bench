# LASR-MCP Data Provenance & Experimental Scopes

**Project:** `mcp-inventory-bench`  
**Manuscript:** *LASR-MCP: Learned Adaptive Schema Resolution with Dynamic In-Tree Recovery for Enterprise Tool-Calling Agents* (v2.0.3)  
**Author:** Anand S. Suchak (Independent Researcher)  

---

## 1. Experimental Scopes Overview

The research artifacts in this repository span three distinct experimental scopes. To maintain strict scientific integrity, raw records are preserved byte-for-byte and never overwritten.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                               EXPERIMENTAL SCOPES                            │
├──────────────────────────────────────────────────────────────────────────────┤
│  SCOPE 1: Historical Frozen Benchmark (N=32 tasks, preliminary single-trial)  │
│  • Storage: datasets/frozen_benchmark_n32/                                   │
│  • Dialect: JSON Schema Draft 2020-12                                        │
│  • Role: Version 1.0 preliminary baseline exploration                        │
│  • Status: Archived historical; offline schema double-counting disclosed     │
├──────────────────────────────────────────────────────────────────────────────┤
│  SCOPE 2: Canonical Live Benchmark (N=3,840 trials, 7,860 live Gemini calls) │
│  • Storage: datasets/fresh_live_benchmark_n32/                               │
│  • Engine: gemini-3.5-flash-lite (temperature=0.2, seed=42)                  │
│  • Protocol: 32 tasks × 6 arms × 20 replicates                              │
│  • Telemetry: 7,860 response-bearing calls + 154 client transport retries    │
│  • Token Accounting: Provider usageMetadata (promptTokenCount + candidates)  │
│  • Status: Authoritative empirical basis for v2.0.3 Table IV & Figures 3–4   │
├──────────────────────────────────────────────────────────────────────────────┤
│  SCOPE 3: Post-Freeze Cross-Schema Stress Test (N=32 tasks across 4 schemas) │
│  • Storage: datasets/cross_schema_validation/                                │
│  • Domains: Procurement, Inventory Adjustment, Freight Shipment, Refund      │
│  • Nature: Deterministic structural simulation-based mechanism stress test   │
│  • Status: Confirms domain-agnostic in-tree recovery mechanics (Table III)   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Dataset Inventory & Provenance

### Scope 1: Historical Frozen Benchmark ($N=32$ Tasks)

- **Directory:** [`datasets/frozen_benchmark_n32/`](../../datasets/frozen_benchmark_n32/)
- **Primary Data File:** `invariant_optimization_summary.json` (388,286 bytes)
  - **SHA-256:** `78c2c88ed5128e0f296fa29e0c258589b516f3adb14b0b8da491fa73bc3ffc11`
- **Origin & Version:** Generated in September 2026 for Version 1.0.
- **Data Nature:** Single-trial execution across 32 tasks.
- **Generating Script:** Historical `trace/run_invariant_optimization.py`.
- **Manuscript Usage:** Historical comparison in Table II and Section II preliminary discussions.
- **Methodological Note:** Token metrics in this historical dataset combined provider prompt tokens with offline heuristic schema approximations ($S_0, \Delta S$), which resulted in double-counting because the Gemini API prompt tokens already encompassed the serialized tool schema. Preserved unchanged for scientific auditing.

---

### Scope 2: Canonical Live Benchmark ($N=3,840$ Trials) — Primary Empirical Basis

- **Directory:** [`datasets/fresh_live_benchmark_n32/`](../../datasets/fresh_live_benchmark_n32/)
- **Benchmark Parameters:**
  - Total completed trials: 3,840
  - Distinct evaluation tasks: 32 (8 per archetype cluster C1–C4)
  - Experimental arms: 6 (`full`, `ci_k0`, `ci_k1_static`, `ci_k1_reactive`, `ci_k2_reactive`, `oracle_reactive`)
  - Fixed-seed executions per task-arm: 20 replicates
  - Execution seed: 42
  - Model: `gemini-3.5-flash-lite` (temperature 0.2)
  - Response-bearing API calls: 7,860
  - Client transport retries: 154
- **Primary Files & Hashes:**
  1. **`benchmark_call_records.jsonl`** (22,105,099 bytes)
     - **SHA-256:** `a50bd0f81c996a6e25b4a994631916a6a8f7f9aae32eed641fc6ef229bdb6a73`
     - **Content:** Exact per-call HTTP payload envelopes, provider `usageMetadata`, prompt/completion token breakdown, round-trip latency, and nested transport retries.
  2. **`benchmark_trial_records.json`** (9,421,879 bytes)
     - **SHA-256:** `245503142784bda97036878ab0fef9bb105bd0b4b8998da2ea7edb804431dddc`
     - **Content:** Complete lifecycle audit for each of the 3,840 trials: task ID, cluster, arm, replicate ID, attempt histories, structural validity, and semantic correctness.
  3. **`benchmark_summary.json`** (5,264 bytes)
     - **SHA-256:** `cdf051693d6452e669f485dec53387046690d017f3513f07524499729722528b`
     - **Content:** Aggregated arm-level summaries across trials.
  4. **`run_manifest.json`** (1,106 bytes)
     - **SHA-256:** `83d36e1bbdeeee9a59e26408368fbb9b7c210bb7643a5ca70feb4a2b6b1d0602`
- **Analysis & Reproduction Scripts:**
  - [`version_2/analyze_fresh_benchmark.py`](../../version_2/analyze_fresh_benchmark.py): Computes the 10,000-resample paired task-cluster bootstrap and 95% confidence intervals.
  - [`version_2/reconcile_canonical_metrics.py`](../../version_2/reconcile_canonical_metrics.py): Read-only audit verifier checking that all manuscript claims match the raw telemetry.
  - [`version_2/generate_paper_tables_v2.py`](../../version_2/generate_paper_tables_v2.py): Deterministically derives Table IV LaTeX from canonical JSON.
- **Manuscript Usage:** Table IV, Figure 3 (Workload comparison and C1 savings), Figure 4 (Retry distribution), Section IV (Empirical Results), and Section VII (Discussion).

---

### Scope 3: Post-Freeze Cross-Schema Stress Test ($N=32$ Tasks)

- **Directory:** [`datasets/cross_schema_validation/`](../../datasets/cross_schema_validation/)
- **Primary Data File:** `cross_schema_results.json` (28,496 bytes)
  - **SHA-256:** `b3d57636f9834ff536204acfe88454c9620228bb67705f1b3caa40e0d562302a`
- **Origin & Nature:** Deterministic structural simulation designed to test whether in-tree JSON Pointer recomposition transfers across 4 enterprise domains without schema-specific heuristics.
- **Generating Script:** `trace/cross_schema_benchmark.py`.
- **Manuscript Usage:** Table III and Section V (Mechanism Transfer).

---

## 3. Cryptographic Verification Instructions

To independently verify the integrity of all raw datasets and telemetry files, execute the following command in PowerShell:

```powershell
python -c "
import hashlib
from pathlib import Path

manifest = Path('release/v2.0.3/MANIFEST.sha256')
with open(manifest, 'r') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'): continue
        expected_hash, filepath = line.split(maxsplit=1)
        p = Path(filepath.strip())
        if not p.exists():
            print(f'MISSING: {p}')
            continue
        actual_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f'TAMPER DETECTED: {p}'
        print(f'VERIFIED: {p.name}')
"
```

---

## 4. Authoritative Publication & Distribution Artifacts

| Artifact | Workspace Path | Size | SHA-256 Checksum | Description |
| :--- | :--- | :---: | :--- | :--- |
| **Authoritative Manuscript** | [`version_2/paper_v2/main_v2.pdf`](../../version_2/paper_v2/main_v2.pdf)<br>[`zenodo_deposit_v2_0_3/LASR_MCP_v2.0.3_Manuscript.pdf`](../../zenodo_deposit_v2_0_3/LASR_MCP_v2.0.3_Manuscript.pdf) | 525,419 B | `73e1b92e1308b57c5760f3b9ef0a2d82355daa1858227a263eca36c0fcece82d` | Complete 15.0-page IEEE conference/transactions preprint |
| **LaTeX Source Bundle** | [`lasr_v2_203_manuscript_bundle.zip`](../../lasr_v2_203_manuscript_bundle.zip)<br>[`zenodo_deposit_v2_0_3/lasr_v2_203_manuscript_bundle.zip`](../../zenodo_deposit_v2_0_3/lasr_v2_203_manuscript_bundle.zip) | 843,694 B | `ae9599564b55a5e19004f32ded7c91fe2b46c480b12914b5343834bcf789044f` | Complete 24-file self-contained LaTeX source bundle |
| **Raw Telemetry Archive** | [`zenodo_deposit_v2_0_3/lasr_v2_203_raw_benchmark_telemetry.zip`](../../zenodo_deposit_v2_0_3/lasr_v2_203_raw_benchmark_telemetry.zip) | 4,319,241 B | `9ee32f32dd332c06b978c4dc37482eebba95216a131961adbbb742b1d1c23b90` | Complete raw 3,840-trial records and 7,860-call JSONL ledgers |
| **Historical V1.0 Draft** | [`paper/main.pdf`](../../paper/main.pdf) | 143,557 B | `f0dd6be85a4dd0e51410886adab2ca98ef3f486a2468305e9ea2fb1cceb22e17` | Historical 8-page preliminary draft (preserved for audit provenance) |
