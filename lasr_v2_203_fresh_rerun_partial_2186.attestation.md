# Detached Release Attestation: LASR-MCP Version 2.0.3 (Fresh Rerun Candidate)

**Candidate Archive**: `lasr_v2_203_fresh_rerun_candidate.zip`  
**Candidate SHA-256**: `3c40a4fc36950dc3e53641066ea30302171b195fa9ebc55c76a9157173c1a939`  
**Candidate Size**: 2,747,113 bytes (662 entries, 556 cache traces, 0 nested zips)  
**Attestation Type**: `DETACHED_POST_PACKAGING_RELEASE_ATTESTATION`  
**Status**: `PARTIAL_RUN — NOT RELEASE-READY` (2,186 Trials Completed across 4,491 Total Live Calls)  

---

## 1. Fresh Live Benchmark Status (Partial Run Under Quota)
- **Protocol**: 20 repetitions $\times$ 32 tasks $\times$ 6 arms = 3,840 planned trials.
- **Provider**: Google Gemini API (`models/gemini-3.5-flash-lite`, resolved `gemini-3.5-flash-lite`, `seed=42`).
- **Response Caching**: Strictly disabled (0 cache hits).
- **Execution Trajectory**:
  - **Completed Trials**: 2,186 / 3,840 trials (56.93% completion across all 6 arms).
  - **Live API Calls Recorded**: 4,491 calls with full `usageMetadata` and separated network vs logical timing.
  - **Halt Trigger**: Keys 2, 3, and 4 exhausted daily limits, and Key 1 encountered depleted prepayment credits (`HTTP 402 / RESOURCE_EXHAUSTED`).
  - **Checkpoint State**: Cleanly flushed to `datasets/fresh_live_benchmark_n32/benchmark_checkpoint.json`.
  - **Resume Command**: `python trace/run_fresh_live_benchmark.py --out-dir datasets/fresh_live_benchmark_n32 --replicates 20 --resume`

### Summary of Completed Trials (N=2,186)
| Arm | Completed Trials | Mean Tokens (P+C) | First-Pass Hierarchical (%) | Final Structural (%) | Workload Savings vs Full (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Full Control | 366 / 640 | 1,130.2 | 80.1% | 100.0% | 0.00% |
| CI $k=0$ | 374 / 640 | 2,060.1 | 0.0% | 86.4% | -82.3% |
| CI $k=1$ static | 359 / 640 | 1,907.4 | 0.0% | 91.4% | -68.8% |
| CI $k=1$ reactive | 367 / 640 | 1,605.2 | 0.0% | 96.7% | -42.0% |
| CI $k=2$ reactive | 367 / 640 | 1,421.3 | 16.9% | 97.0% | -25.7% |
| Oracle reactive | 353 / 640 | 1,387.8 | 21.5% | 96.3% | -22.8% |

### 10,000-Resample Clustered Bootstrap (Completed Trials)
- **Primary Comparison**: LASR $k=2$ reactive vs Full Control over 32 task clusters
- **Token Savings Point Estimate**: -25.94%
- **95% Bootstrap Confidence Interval**: `[-52.55%, -3.16%]`
- **Final Structural Success Difference**: $-3.00\%$
- **First-Pass Hierarchical Difference**: $-63.20\%$
- **Status**: The full 3,840-trial benchmark is required to reach pre-specified statistical power.

---

## 2. Telemetry Pilot & Static Audit Verification
- **Static Formula Audit**: Checked all repository files. 0 forbidden double-counting formulas detected.
- **Telemetry Pilot Verification**: Verified 100% of 9 live calls in `datasets/dataset_pilot_telemetry/` have complete `usageMetadata`, explicit schema presence, verified seeds, and additive multi-attempt summation.
- **Integrity Verifier**: 9/9 checks in `version_2/verify_version_2_integrity.py` passed (Exit code 0).
- **Regression Suite**: 36/36 tests in `version_2/test_verifier_regressions.py` passed (Exit code 0).

---

## 3. Byte-for-Byte Preservation of Historical Baselines
All historical baseline archives and datasets remain byte-for-byte identical to their pinned hashes:
- `lasr_v2_203_reconciled_candidate.zip`: `513d40e5c7e8630a44d957b87121de22261cebff2c28ac106387925c78a84452`
- `lasr_v2_203_final_candidate.zip`: `811bd1864ea6889931ecdc337372a0a0639e4bbb88bf7950f66967e3a1ebd457`
- `datasets/frozen_benchmark_n32/invariant_optimization_summary.json`: `78c2c88ed5128e0f296fa29e0c258589b516f3adb14b0b8da491fa73bc3ffc11`
- `datasets/frozen_benchmark_n32/MANIFEST.sha256`: `71e87aeefc5b10f7b5bc99571ecaf430b24b9f1811fa4dd3d47af50e84951c0b`
- `datasets/cross_schema_validation/cross_schema_results.json`: `b3d57636f9834ff536204acfe88454c9620228bb67705f1b3caa40e0d562302a`
