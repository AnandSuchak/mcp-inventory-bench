# Cryptographic Release Attestation: LASR-MCP Version 2.0.3 Reconciled Candidate

**Attestation Type:** `DETACHED_POST_PACKAGING_RELEASE_ATTESTATION`  
**Release Version:** `2.0.3`  
**Candidate Name:** `lasr_v2_203_reconciled_candidate.zip`  
**Attestation Timestamp:** 2026-10-23T10:56:00+05:30  
**Verification Stage:** `clean_extraction_verification`  

---

## 1. Cryptographic Hash & Archive Metadata

| Property | Value | Status |
| :--- | :--- | :--- |
| **Archive Filename** | `lasr_v2_203_reconciled_candidate.zip` | MATCH |
| **Archive SHA-256** | `513d40e5c7e8630a44d957b87121de22261cebff2c28ac106387925c78a84452` | COMPUTED |
| **Archive File Size** | `729,505` bytes (~0.70 MB) | VALIDATED |
| **Total Archive Entries** | `647` entries | VALIDATED |
| **Recorded Cache Traces** | `556` JSON traces (all in `datasets/cache/`) | EXACT MATCH (556/556) |
| **Zip Integrity Test** | `ZipFile.testzip() == None` | PASSED (Zero corruption) |
| **Duplicate Path Entries** | `0` | PASSED |
| **Nested ZIP Archives** | `0` (Zero nested archives) | PASSED |
| **Transient LaTeX Files** | `0` (Zero `.aux`, `.log`, `.fls`, `.bbl`, etc.) | PASSED |
| **Detached Sidecars in ZIP** | `0` (Attestations strictly external) | PASSED |

---

## 2. Independent Clean-Extraction Verification Results (9/9 Checks Passed)

The candidate archive `lasr_v2_203_reconciled_candidate.zip` was extracted into an isolated clean temporary directory and evaluated directly against `version_2/verify_version_2_integrity.py --stage clean_extraction_verification`:

| Check ID | Verification Area | Result | Evidence / Details |
| :---: | :--- | :---: | :--- |
| **1** | **Cryptographic Provenance & Manifests** | **PASS** | Validated `datasets/frozen_benchmark_n32/MANIFEST.sha256` hash `71e87aee...` (single `invariant_optimization_summary.json` entry); validated `metadata.json` hash `ab8ca76d...` independently; pinned hashes `78c2c88e...` and `b3d57636...` matched. Strict traversal and duplicate guards passed. |
| **2** | **Reconciled Token Metric Sums** | **PASS** | Recomputed attempt sums using canonical definition $\text{recorded\_prompt\_candidate\_tokens} = \text{prompt\_tokens} + \text{completion\_tokens}$: Full Schema = 61,853 tokens (30/32 final, 10/32 first-pass structural: 31.3%, hierarchical: 31.3%), LASR $k=1$ = 51,594 tokens (32/32, hierarchical 15.6%), LASR $k=2$ = 50,276 tokens (32/32, hierarchical 18.8%). |
| **3** | **Dual Metric Token Reconciliation** | **PASS** | Primary prompt-plus-candidate workload token savings = $18.72\%$ ($50,276$ vs $61,853$); Conditional Tokens-to-Success (TTS) savings = $15.73\%$ ($1,571.1$ vs $1,864.4$). |
| **4** | **Empirical Latency Hierarchy** | **PASS** | 556 cache traces: $p_{50} = 3,407.11\text{ ms}$, mean $= 7,752.79\text{ ms}$. 1,000 AST runs: $p_{50} = 20.1\ \mu\text{s}$, $p_{99} = 46.1\ \mu\text{s}$. Ratio $= 0.00059\%$ of request $p_{50}$. |
| **5** | **Diagnostic Retrieval Curves** | **PASS** | TF-IDF: $k=1$ (10.94%), $k=2$ (15.62%, 21/32 zero), $k=3$ (27.08%), $k=5$ (30.21%). LSA: $k=1$ (9.90%), $k=2$ (16.15%, 21/32 zero), $k=3$ (24.48%), $k=5$ (35.42%). Evaluated with normalized C4 gold aliases; query-inclusive/transductive TF-IDF and inductive LSA protocols documented. |
| **6** | **LangGraph Counterfactual Model** | **PASS** | State-accumulation token model with recorded P+C tokens: 69,119 tokens (+11.75% overhead vs Full; LASR $k=2$ savings = 27.26%). |
| **7** | **Formal Proof Source Invariants** | **PASS** | Correct general bound $K \le M - |A_0|$ verified; `IEEEproof` environment confirmed; depth bound $K \le D$ disproven via sibling leaf counterexample. |
| **8** | **Canonical Metric Reconciliation** | **PASS** | `reconcile_canonical_metrics.py --check` passed read-only audit. Manuscript LaTeX tables, CSV, and JSON snapshots verified against in-memory generator; catches cell tampering. |
| **9** | **Behavioral Packaging & Structure** | **PASS** | Production validator confirmed 647 entries, 556 cache traces, 0 nested zips, root `create_audit_zip.py`. |

---

## 3. Comprehensive Regression & Negative Mutation Suite (35/35 Tests Passed)

Evaluated in clean-extraction environment via `version_2/test_verifier_regressions.py`:

1. `[PASS]` Manifest Directory Traversal Rejection (`..` & absolute paths)
2. `[PASS]` Manifest Duplicate Entry Rejection
3. `[PASS]` Manifest Corrupted Hash Detection
4. `[PASS]` Manifest Missing Sibling Metadata Rejection
5. `[PASS]` Archive Validator Required Path Omission Rejection
6. `[PASS]` Archive Validator Nested ZIP Rejection
7. `[PASS]` Archive Validator Stale In-Package Attestation Rejection
8. `[PASS]` Canonical Table Metric Tampering Detection
9. `[PASS]` Table IV Invariant Floor Tampering Detection
10. `[PASS]` Stale Derived Summary Detection
11. `[PASS]` Non-Finite & Boolean Latency Value Rejection
12. `[PASS]` Multi-Arm Task ID Mismatch Rejection
13. `[PASS]` Missing Packager Subprocess & Structured Certificate Failure
14. `[PASS]` H1 JSON Summary Metric Tampering Detection
15. `[PASS]` H1 JSON Per-Task Row Prediction Tampering Detection
16. `[PASS]` H1 CSV Metric Tampering Detection
17. `[PASS]` Canonical H1 Subtree Tampering Detection
18. `[PASS]` Missing H1 Evaluation File Rejection
19. `[PASS]` Retrieval CSV Curve Tampering Detection
20. `[PASS]` Retrieval JSON Macro Recall Tampering Detection
21. `[PASS]` Canonical Retrieval Subtree Tampering Detection
22. `[PASS]` Table I Init S0 / Exp Delta S Tampering Detection
23. `[PASS]` Table I Structural Success Rate Tampering Detection (100% -> 5%)
24. `[PASS]` Table II Exact McNemar p-value Tampering Detection
25. `[PASS]` Table III Cluster Lift Tampering Detection
26. `[PASS]` Table III C1 Cell Tampering Detection (87.5% -> 7.5%)
27. `[PASS]` Frozen Manifest Integrity & Tampering Detection
28. `[PASS]` Frozen Benchmark Metadata Tampering Detection
29. `[PASS]` CLI Script `--help` and Dry-Run Immutability Verification
30. `[PASS]` RELEASE_VERSION Missing/Empty Fail-Closed Verification
31. `[PASS]` Zero-Mutation Source Immutability During Verification
32. `[PASS]` Negative Mutation 1: Injected Heuristic Schema Tokens Fails
33. `[PASS]` Negative Mutation 2: Bypassed Hierarchical Conjunction Fails
34. `[PASS]` Negative Mutation 3: Manuscript Table Tampering Fails
35. `[PASS]` Negative Mutation 4: Required Limitation / Provenance Omission Fails

---

## 4. Reconciled Primary Metrics & Exploratory Sensitivity Replication

### Primary Frozen Benchmark ($N=32$)
- **Recorded P+C Token Subtotal**:
  - Full Schema: **61,853**
  - Context Injection ($k=0$): **70,541** (-14.05% vs Full)
  - Context Injection ($k=1$ static): **56,947** (+7.93% vs Full)
  - LASR $k=1$ reactive: **51,594** (+16.59% vs Full)
  - LASR $k=2$ reactive: **50,276** (+18.72% vs Full)
  - Oracle reactive: **50,578** (+18.23% vs Full)
- **Conditional Mean TTS (P+C tokens)**:
  - Full: **1,864.4**
  - $k=0$: **2,196.7** (-17.82%)
  - $k=1$ static: **1,631.0** (+12.52%)
  - $k=1$ reactive: **1,612.3** (+13.52%)
  - $k=2$ reactive: **1,571.1** (+15.73%)
  - Oracle: **1,554.0** (+16.65%)
- **Hierarchical First-Pass Success Rate ($\text{Structural} \land \text{Semantic}$)**:
  - Full: **10/32 (31.3%)**
  - $k=0$: **0/32 (0.0%)**
  - $k=1$ static: **5/32 (15.6%)**
  - $k=1$ reactive: **5/32 (15.6%)**
  - $k=2$ reactive: **6/32 (18.8%)**
  - Oracle: **5/32 (15.6%)**

### Exploratory Sensitivity Live Replication
- **API Model Target**: Google Gemini API (`gemini-3.5-flash-lite`)
- **Total Recorded Attempts**: 428 across 6 experimental arms
- **Unique Live API Responses**: 285 newly observed entries; within-run cache reuse accounted for 143 attempts.
- **Observed Live Savings**:
  - LASR $k=1$ reactive: **52,389** tokens (+5.69% vs Full 55,549)
  - LASR $k=2$ reactive: **51,224** tokens (+7.79% vs Full 55,549)
- **Statistical Significance**: Paired bootstrap intervals cross zero (95% CI: $k=1$ [-13.2%, +24.4%]; $k=2$ [-11.0%, +26.3%]). Documented strictly as exploratory replication/sensitivity test, not identical point reproduction.
- **Telemetry Boundaries**: Provider usageMetadata and decoding seed ($42$) were not captured in recorded live cache format; `lat` reflects client logical-call wall time.

---

## 5. Historical Release & Baseline Dataset Preservation Matrix

| Release / Asset | Archive / File | Expected SHA-256 | Actual SHA-256 | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Version 2.0.0 Release** | `lasr_v2_audit_bundle.zip` | `36cf1def3de7bde589c02839b26ed10ac0fb2ec923eaffb46282e96e43fd00f3` | `36cf1def3de7bde589c02839b26ed10ac0fb2ec923eaffb46282e96e43fd00f3` | **MATCH** |
| **Version 2.0.1 Release** | `lasr_v2_audit_bundle_v2.0.1.zip` | `43e9f09cceeb55407c8639777648f98d630059cb6bf64fe2b38121704e58bd71` | `43e9f09cceeb55407c8639777648f98d630059cb6bf64fe2b38121704e58bd71` | **MATCH** |
| **Version 2.0.2 Release** | `lasr_v2_audit_bundle_v2.0.2.zip` | `4e916c6216473c7cfdf1185d58000bbb3ece709325599c287430df8a12064be8` | `4e916c6216473c7cfdf1185d58000bbb3ece709325599c287430df8a12064be8` | **MATCH** |
| **Version 2.0.3 Release** | `lasr_v2_audit_bundle_v2.0.3.zip` | `22183ed47f596373324ba09889bc5f54dd5b2012b3fa4d0d602210a8b2d4b138` | `22183ed47f596373324ba09889bc5f54dd5b2012b3fa4d0d602210a8b2d4b138` | **MATCH** |
| **Review Candidate** | `lasr_v2_203_closure_candidate.zip` | `d43c20a7b32d13e17bba03d7e1d05a1824413db13f859d08d01179697e2bce50` | `d43c20a7b32d13e17bba03d7e1d05a1824413db13f859d08d01179697e2bce50` | **MATCH** |
| **Final Candidate** | `lasr_v2_203_final_candidate.zip` | `811bd1864ea6889931ecdc337372a0a0639e4bbb88bf7950f66967e3a1ebd457` | `811bd1864ea6889931ecdc337372a0a0639e4bbb88bf7950f66967e3a1ebd457` | **MATCH** |
| **Frozen Primary Manifest** | `datasets/frozen_benchmark_n32/MANIFEST.sha256` | `71e87aeefc5b10f7b5bc99571ecaf430b24b9f1811fa4dd3d47af50e84951c0b` | `71e87aeefc5b10f7b5bc99571ecaf430b24b9f1811fa4dd3d47af50e84951c0b` | **MATCH** |
| **Frozen Primary Evidence** | `invariant_optimization_summary.json` | `78c2c88ed5128e0f296fa29e0c258589b516f3adb14b0b8da491fa73bc3ffc11` | `78c2c88ed5128e0f296fa29e0c258589b516f3adb14b0b8da491fa73bc3ffc11` | **MATCH** |
| **Frozen Benchmark Metadata** | `datasets/frozen_benchmark_n32/metadata.json` | `ab8ca76d5ef47826ba95d28046b1b6181f001055fccf2490e659102249f72c91` | `ab8ca76d5ef47826ba95d28046b1b6181f001055fccf2490e659102249f72c91` | **MATCH** |
| **Cross-Schema Evidence** | `cross_schema_results.json` | `b3d57636f9834ff536204acfe88454c9620228bb67705f1b3caa40e0d562302a` | `b3d57636f9834ff536204acfe88454c9620228bb67705f1b3caa40e0d562302a` | **MATCH** |
| **Cache Traces (556)** | `datasets/cache/*.json` | Finite, non-negative, non-boolean latencies | 556 files verified | **MATCH** |

---

## 6. Attestation Sign-off

The archive `lasr_v2_203_reconciled_candidate.zip` implements the metric corrections and manuscript reconciliation required by the independent audit:
- The double-counted heuristic schema tokens have been removed from the recorded prompt-plus-candidate token subtotal.
- First-pass hierarchical success is strictly derived as $\text{first\_pass\_structural} \land \text{first\_pass\_semantic}$.
- The manuscript, tables, CSV snapshots, and canonical metrics reflect these exact values.
- The live rerun is accurately characterized as exploratory sensitivity replication (285 unique live API responses + cache reuse).
- Four negative mutation tests demonstrate fail-closed rejection of formula, hierarchical, table, and provenance tampering.
- Clean-room extraction passes all 9 integrity checks and all 35 regression tests.
- All historical releases, candidates, and raw frozen evidence remain untouched byte-for-byte.
