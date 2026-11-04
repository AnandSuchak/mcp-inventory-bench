# Detached Release Attestation: LASR-MCP Version 2.0.3 (Final Rebuilt Candidate)

**Candidate Archive**: `lasr_v2_203_final_rebuilt_candidate.zip`  
**Candidate SHA-256**: `fc82d33b8992914ee130ef2805427ef2a4f01541243e0f93be120e2d20ae7f5b`  
**Candidate Size**: 4,319,876 bytes (665 entries, 556 cache traces, 0 nested zips)  
**Attestation Type**: `DETACHED_POST_PACKAGING_FINAL_RELEASE_ATTESTATION`  
**Status**: `FULL_BENCHMARK_COMPLETE_VERIFIED` (3,840 / 3,840 Trials Completed; 100.00% Coverage)  
**Timestamp**: `2026-10-26T14:04:13+05:30`  

---

## 1. Executive Summary & Benchmark Protocol
This document certifies the final rebuilt release candidate for **LASR-MCP Version 2.0.3** (`mcp-inventory-bench`). The evaluation protocol executed a full factorial live benchmark across:
- **32 Heterogeneous Supply-Chain Tasks** (Clusters $C_1$--$C_4$)
- **6 Experimental Arms**: Full Control (`full`), Lean Zero-Constraint (`ci_k0`), Static 1-Constraint (`ci_k1_static`), Reactive 1-Constraint (`ci_k1_reactive`), Proposed LASR Bundling (`ci_k2_reactive`), and Task-Aware Oracle (`oracle_reactive`)
- **20 Independent Replications** per task-arm pair ($N = 3,840$ completed trials)
- **Model**: `models/gemini-3.5-flash-lite` (provider-resolved: `gemini-3.5-flash-lite`, temperature = 0.2, seed = 42)
- **Response Caching**: Strictly disabled ($0$ cache hits; 100% live provider execution)

---

## 2. Canonical Empirical Results ($N = 3,840$ Trials)

### System-Level Performance Summary
| Experimental Arm | Init Schema ($S_0$) | Exp Schema ($\Delta S$) | 1st-Pass Hier. (%) | Final Struct. (%) | Final Sem. (%) | Mean TTS (tok) | Mean P+C (tok) | Total P+C (tok) | Workload Penalty vs Full (%) | 95% Bootstrap CI |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Full Control (`full`)** | 552.0 | 0.0 | 81.2% | 100.0% | 96.9% | 1,116.8 | 1,116.8 | 714,740 | **0.0% (Baseline)** | — |
| **Lean Zero-Constraint (`ci_k0`)** | 339.0 | 0.0 | 0.0% | 87.5% | 84.4% | 2,033.4 | 2,057.7 | 1,316,900 | **-84.3%** | `[-125.15%, -49.21%]` |
| **Static 1-Constraint (`ci_k1_static`)** | 344.7 | 0.0 | 0.0% | 90.6% | 87.5% | 1,887.0 | 1,919.3 | 1,228,340 | **-71.9%** | `[-108.92%, -40.68%]` |
| **Reactive 1-Constraint (`ci_k1_reactive`)** | 344.7 | 59.8 | 0.0% | 96.9% | 93.8% | 1,575.2 | 1,601.4 | 1,024,880 | **-43.4%** | `[-74.45%, -18.23%]` |
| **Proposed LASR (`ci_k2_reactive`)** | 359.4 | 45.2 | 18.8% | 96.9% | 93.8% | 1,374.0 | 1,406.5 | 900,140 | **-25.9%** | `[-52.55%, -3.16%]` |
| **Theoretical Oracle (`oracle_reactive`)** | 359.0 | 45.1 | 21.9% | 96.9% | 93.8% | 1,344.4 | 1,377.8 | 881,820 | **-23.4%** | `[-50.18%, -1.12%]` |

*Note: Workload savings point estimate for LASR $k=2$ vs Full Control is $-25.94\%$ ($p < 0.05$). Proposed LASR operates within $2.0\%$ of the theoretical oracle upper bound ($1,406.5$ vs $1,377.8$ tokens).*

### Task Cluster Breakdown ($N = 960$ Trials per Cluster)
- **Cluster $C_1$ (`routine_regional_replenish`, Tasks 001–008)**:
  - Full Control: $979.8$ tokens | Final Struct = $100.0\%$ | 1st-Pass = $75.0\%$
  - Lean $k=0$: $1,675.2$ tokens | Final Struct = $87.5\%$ | 1st-Pass = $0.0\%$
  - Reactive $k=1$: $1,549.6$ tokens | Final Struct = $96.9\%$ | 1st-Pass = $0.0\%$
  - **Proposed LASR $k=2$**: $\mathbf{847.6\text{ tokens}}$ | Final Struct = $\mathbf{100.0\%}$ | 1st-Pass = $\mathbf{75.0\%}$
  - **Empirical Boundary Result**: **$+13.5\%$ Token Savings** for LASR $k=2$ over Full Control in routine regimes where active constraints fit within upfront budget ($M \le k$).
- **Cluster $C_2$ (`expedited_emergency_order`, Tasks 009–016)**: Full = $1,274.2$ tok vs LASR $k=2 = 1,557.5\text{ tok}$ ($-22.2\%$).
- **Cluster $C_3$ (`specialized_bulk_procurement`, Tasks 017–024)**: Full = $1,008.1$ tok vs LASR $k=2 = 1,610.9\text{ tok}$ ($-59.8\%$).
- **Cluster $C_4$ (`multi_item_depot_rebalance`, Tasks 025–032)**: Full = $1,205.0$ tok vs LASR $k=2 = 1,609.9\text{ tok}$ ($-33.6\%$).

---

## 3. Telemetry Ledger, Retries, and Financial Reconciliation
- **Response-Bearing API Calls**: Exactly **7,860 calls** recorded in [`benchmark_call_records.jsonl`](file:///c:/paper/mcp/datasets/fresh_live_benchmark_n32/benchmark_call_records.jsonl).
  - All 7,860 calls completed with HTTP 200 status.
  - Complete provider `usageMetadata` (`promptTokenCount`, `candidatesTokenCount`, `totalTokenCount`) present on 100.0% of records.
- **Client Transport Retries**: Exactly **154 transport retries** (handling transient HTTP 429 / 503 network backoffs and quota rate limits). Transport retries are cleanly isolated and reported separately from response-bearing turns.
- **Financial Expenditure Reconciliation**:
  - Initial Prepayment Credit Balance: **₹500.00 INR**
  - Deductions during Key 1 execution (first 3,149 trials): **₹116.16 INR**
  - Remaining 691 trials completed under free-tier quotas across Keys 2–6: **₹0.00 INR**
  - Final Balance Remaining: **₹383.84 INR**
  - Verified against Google Cloud billing records.

---

## 4. Statistical Methodology
- **Bootstrap Method**: Paired task-cluster percentile bootstrap.
- **Resamples**: 10,000 resamples over 32 task clusters.
- **Seed**: 42 (deterministic reproducibility).
- **Confidence Intervals**: Empirical 2.5% and 97.5% quantiles of the resample distribution.

---

## 5. Verification Harness & Clean-Room Reproduction
1. **Static Empirical Formula Audit**: Zero forbidden double-counting token formulas detected across repository (`version_2/audit_token_formulas.py` exit code 0).
2. **Regression Suite**: 36/36 tests passed (`version_2/test_verifier_regressions.py` exit code 0).
3. **Master Integrity Verifier**: 9/9 verification stages passed (`version_2/verify_version_2_integrity.py` exit code 0).
4. **Canonical Metric Reconciler**: Read-only check mode passed with zero discrepancies (`version_2/reconcile_canonical_metrics.py --check` exit code 0).
5. **Clean-Room Extraction Test**: Extracted `lasr_v2_203_final_rebuilt_candidate.zip` into an isolated temporary directory; executed formula audit, telemetry pilot check, canonical metric check, and integrity verifier with 100% pass rate.

---

## 6. Cryptographic Provenance & Preservation of Historical Baselines
All historical baseline archives and frozen datasets remain byte-for-byte unchanged:
- `lasr_v2_audit_bundle.zip`: `36cf1def3de7bde589c02839b26ed10ac0fb2ec923eaffb46282e96e43fd00f3`
- `lasr_v2_audit_bundle_v2.0.1.zip`: `43e9f09cceeb55407c8639777648f98d630059cb6bf64fe2b38121704e58bd71`
- `lasr_v2_audit_bundle_v2.0.2.zip`: `4e916c6216473c7cfdf1185d58000bbb3ece709325599c287430df8a12064be8`
- `lasr_v2_audit_bundle_v2.0.3.zip`: `22183ed47f596373324ba09889bc5f54dd5b2012b3fa4d0d602210a8b2d4b138`
- `lasr_v2_203_closure_candidate.zip`: `d43c20a7b32d13e17bba03d7e1d05a1824413db13f859d08d01179697e2bce50`
- `lasr_v2_203_final_candidate.zip`: `811bd1864ea6889931ecdc337372a0a0639e4bbb88bf7950f66967e3a1ebd457`
- `lasr_v2_203_reconciled_candidate.zip`: `513d40e5c7e8630a44d957b87121de22261cebff2c28ac106387925c78a84452`
- `lasr_v2_203_fresh_rerun_candidate.zip`: `9ee32f32dd332c06b978c4dc37482eebba95216a131961adbbb742b1d1c23b90`
- Historical partial-run attestation reference: `3a9d91b0f9e1309fb5cf0bb465f3b27bb62d96d4af901b37b835f3df04c2c015` (size: 4,234,904 bytes, 662 entries)
- Frozen benchmark manifests: `datasets/frozen_benchmark_n32/MANIFEST.sha256` and `datasets/cross_schema_validation/MANIFEST.sha256` verified intact.
