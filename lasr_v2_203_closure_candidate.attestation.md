# LASR-MCP Version 2.0.3 Closure Candidate Attestation Report

**Release Archive:** `lasr_v2_203_closure_candidate.zip`  
**Release Version:** `2.0.3`  
**Candidate Identifier:** `lasr_v2_203_closure_candidate`  
**Audit Stage:** `clean_extraction_verification`  
**Attestation Timestamp:** `2026-10-20T19:28:01+05:30`  
**Status:** `ALL_CHECKS_PASSED` (9/9 Master Checks Passed, 26/26 Regression Tests Passed, Exit Code: 0, Zero Source File Mutations)

---

## 1. Archive Cryptographic Provenance

| Property | Value | Status |
| :--- | :--- | :---: |
| **Archive File** | `lasr_v2_203_closure_candidate.zip` | Verified |
| **SHA-256 Checksum** | `d43c20a7b32d13e17bba03d7e1d05a1824413db13f859d08d01179697e2bce50` | Certified |
| **Archive Byte Size** | 674,352 bytes (0.64 MB) | Verified |
| **Total Archive Entries** | 645 members | Verified |
| **Cache Execution Traces** | Exactly 556 JSON traces in `datasets/cache/` | Verified |
| **ZIP Structural Integrity** | Clean CRC (`ZipFile.testzip() == None`) | Verified |
| **Nested ZIP Archives** | Exactly 0 | Verified |
| **Transient LaTeX Artifacts** | Exactly 0 (clean build policy) | Verified |
| **Detached Sidecars in ZIP** | Exactly 0 (attestations remain detached outside ZIP) | Verified |

---

## 2. Clean-Extraction Verification Results

Verification executed inside a fresh, isolated temporary directory (`tmpn0wardig`):

```
================================================================================
LASR-MCP VERSION 2.0.3: DEEP INTEGRITY & BEHAVIORAL VERIFICATION AUDIT
Audit Stage: clean_extraction_verification
Timestamp:   2026-10-20T19:28:01.255600+05:30
================================================================================
[PASS] 1. Cryptographic Provenance: Manifests parsed and verified against disk files; pinned hashes matched.
[PASS] 2. Primary Token Accounting: Full=96629, k1=77140, k2=75248 (Final success: Full=30/32, k2=32/32)
[PASS] 3. Dual Token Metrics: Workload Savings=22.13%, TTS Savings=19.28%
[PASS] 4. Empirical Latency: 556 Cache Traces p50=3407.1ms, 1000 AST Runs p50=20.1us, AST Ratio=0.00059% (<0.001%)
[PASS] 5. Retrieval Baselines Recomputed: TF-IDF=15.6% (21/32 zero-hits), LSA SVD=16.1% (21/32 zero-hits)
[PASS] 6. LangGraph Model Audit: Total=103895 tok, Overhead=+7.52%, LASR k=2 Savings=27.57%
[PASS] 7. Formal Proof Source Invariant: K<=M-|A0| Established with IEEEproof and Sibling Leaf Counterexample
[PASS] 8. Canonical Metric Audit: Pure read-only reconciliation passed.
[PASS] 9. Behavioral Packaging: Packager executed, zip validated via production validator, 0 nested zips.
================================================================================
ALL 9 VERIFICATION CHECKS PASSED SUCCESSFULLY.
Audit Certificate (clean_extraction_verification) saved to verification_audit_certificate.json
================================================================================
```

### Automated Regression & Negative Test Suite:
`version_2/test_verifier_regressions.py`: **26/26 PASSED** (exit code 0)
1. Manifest Directory Traversal Rejection ('..' & absolute): PASS
2. Manifest Duplicate Entry Rejection: PASS
3. Manifest Corrupted Hash Detection: PASS
4. Manifest Missing Sibling Metadata Rejection: PASS
5. Archive Validator Required Path Omission Rejection: PASS
6. Archive Validator Nested ZIP Rejection: PASS
7. Archive Validator Stale In-Package Attestation Rejection: PASS
8. Canonical Table Metric Tampering Detection: PASS
9. Table IV Invariant Floor Tampering Detection: PASS
10. Stale Derived Summary Detection: PASS
11. Non-Finite & Boolean Latency Value Rejection: PASS
12. Multi-Arm Task ID Mismatch Rejection: PASS
13. Missing Packager Subprocess & Structured Certificate Failure: PASS
14. H1 JSON Summary Metric Tampering Detection: PASS
15. H1 JSON Per-Task Row Prediction Tampering Detection: PASS
16. H1 CSV Metric Tampering Detection: PASS
17. Canonical H1 Subtree Tampering Detection: PASS
18. Missing H1 Evaluation File Rejection: PASS
19. Retrieval CSV Curve Tampering Detection: PASS
20. Retrieval JSON Macro Recall Tampering Detection: PASS
21. Canonical Retrieval Subtree Tampering Detection: PASS
22. Table I Init S0 / Exp Delta S Tampering Detection: PASS
23. Table I Structural Success Rate Tampering Detection: PASS
24. Table II Exact McNemar p-value Tampering Detection: PASS
25. Table III Cluster Lift Tampering Detection: PASS
26. Zero-Mutation Source Immutability During Verification: PASS

---

## 3. Scientific Metrics Certified

- **Workload Token Reduction**: 22.13% net savings for LASR-MCP ($k=2$ reactive: 75,248 tokens vs. Full Schema: 96,629 tokens across 32 tasks).
- **Conditional Tokens-to-Success (TTS)**: 19.28% savings (mean 2,351.5 tokens vs. 2,913.2 tokens).
- **Final Structural Success**: 100.0% (32/32 tasks) for both LASR reactive configurations ($k=1$ and $k=2$) compared with 93.8% (30/32 tasks) for full schema.
- **Empirical Request Latency Hierarchy**: Median request turnaround $p_{50} = 3,407.11\text{ ms}$, mean $= 7,752.79\text{ ms}$, $p_{90} = 14,737.95\text{ ms}$, $p_{99} = 56,708.45\text{ ms}$ over 556 cache traces.
- **AST Parsing Overhead**: Median AST pipeline latency $p_{50} = 20.1\ \mu\text{s}$ ($0.0201\text{ ms}$), $p_{99} = 46.1\ \mu\text{s}$, representing $0.00059\%$ of network request turnaround.
- **Diagnostic Retrieval Baselines (Normalized C4 Aliases)**:
  - Top-2 Macro Recall: TF-IDF $= 15.62\%$, LSA/SVD $= 16.15\%$.
  - Zero-hit tasks at $k=2$: exactly 21 of 32 tasks.
- **Hypothesis H1 Intent-Conditioned Constraint Predictor**:
  - $\Delta F_1 = +0.6125$ ($+0.613$ display), 95% bootstrap CI $[+0.419, +0.781]$.
  - Monte Carlo one-sided paired sign-flip permutation test ($B=10,000$, seed $42$): $p = (0+1)/(10001) \approx 0.0001$ ($p < 0.001$).
  - Four-cluster sensitivity analysis: equal-weight cluster delta $+0.6125$, exhaustive 16 sign flips $p = 2/16 = 0.125$, confirming task-level significance is template-family specific with recurring constraint combinations.
- **LangGraph Counterfactual Accumulation Model**: Total $= 103,895\text{ tokens}$ (+7.52% overhead vs. full schema; net savings $-7.52\%$). LASR $k=2$ achieves $27.57\%$ workload-token savings relative to LangGraph accumulation.
- **Cross-Schema Simulation Stress Test**: 22.5% pooled savings ($54,657 \rightarrow 42,369$ tokens across 64 records); 4-domain macro savings $= 22.3\%$; 3-new-domain macro savings $= 22.7\%$.

---

## 4. Historical Release Baseline Preservation

| Archive | Certified SHA-256 | Status |
| :--- | :--- | :---: |
| `lasr_v2_audit_bundle.zip` (v2.0.0) | `36cf1def3de7bde589c02839b26ed10ac0fb2ec923eaffb46282e96e43fd00f3` | Preserved |
| `lasr_v2_audit_bundle_v2.0.1.zip` | `43e9f09cceeb55407c8639777648f98d630059cb6bf64fe2b38121704e58bd71` | Preserved |
| `lasr_v2_audit_bundle_v2.0.2.zip` | `4e916c6216473c7cfdf1185d58000bbb3ece709325599c287430df8a12064be8` | Preserved |
| `lasr_v2_audit_bundle_v2.0.3.zip` (prior candidate) | `22183ed47f596373324ba09889bc5f54dd5b2012b3fa4d0d602210a8b2d4b138` | Preserved |
| `lasr_v2_203_closure_candidate.zip` (fresh closure candidate) | `d43c20a7b32d13e17bba03d7e1d05a1824413db13f859d08d01179697e2bce50` | Generated & Verified |
