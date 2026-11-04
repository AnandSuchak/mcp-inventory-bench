# LASR-MCP Version 2.0.3 Release Notes

**Release Version:** `2.0.3`  
**Date:** 2026-10-18  
**Branch:** `v2.0.3-assume-audit-closure`  
**Subject:** Consolidated Assume-Loop Audit Closure & Attestation Hardening

---

## 1. Executive Summary

LASR-MCP Version 2.0.3 represents the consolidated closure patch completing the internal assume-loop verification cycle. Version 2.0.3 resolves all actionable audit findings from the technical review without modifying any frozen raw experimental records or Version 1 files.

### Key Quality & Verification Invariants Guaranteed:
1. **Pristine Baseline Preservation**:
   - `lasr_v2_audit_bundle.zip` (SHA-256 `36cf1def...`), `lasr_v2_audit_bundle_v2.0.1.zip` (SHA-256 `43e9f09c...`), `lasr_v2_audit_bundle_v2.0.2.zip` (SHA-256 `4e916c62...`), and `lasr_v2_203_final_candidate.zip` (SHA-256 `811bd186...`) remain 100% byte-for-byte untouched.
   - Version 1 core trees (`paper/`, `trace/`, `README.md`, `datasets/frozen_benchmark_n32/`) remain 100% preserved. `datasets/frozen_benchmark_n32/MANIFEST.sha256` is restored byte-for-byte to baseline Version 2.0.0 hash `71e87aeefc5b10f7b5bc99571ecaf430b24b9f1811fa4dd3d47af50e84951c0b` (listing only `invariant_optimization_summary.json`), with `metadata.json` (`ab8ca76d...`) validated independently.
2. **Crash-Proof Verifier Architecture**:
   - Structured check results eliminate any `UnboundLocalError` vulnerabilities when files are missing or malformed.
   - Strict manifest validation rejects path traversal (`..`), absolute paths, duplicate entries, malformed hex hashes, and empty paths.
   - All failure-mode and regression tests pass in `version_2/test_verifier_regressions.py`.
3. **Canonical Metric Reconciliation & Read-Only Auditing**:
   - Programmatic pipeline `version_2/reconcile_canonical_metrics.py` separates `--check` (pure read-only audit, never modifies files) from `--regenerate`.
   - Primary token metric is defined strictly as provider-recorded prompt-plus-candidate token subtotal ($\text{prompt\_tokens} + \text{completion\_tokens}$, Full: 61,853; $k=1$: 51,594; $k=2$: 50,276), eliminating heuristic schema double-counting.
   - Standardized first-pass hierarchical success as $\text{first\_pass\_structural} \land \text{first\_pass\_semantic}$ (Full: 10/32; $k=1$: 5/32; $k=2$: 6/32).
   - Deep cell-level table comparison: verifies shipped LaTeX tables byte-for-byte against in-memory generated tables.
   - Documented exploratory live replication and sensitivity analysis (285 unique live API responses + cache reuse, live P+C savings point estimates: 5.69% for $k=1$, 7.79% for $k=2$, with paired bootstrap intervals crossing zero).
4. **Diagnostic Retrieval Curves with Normalized C4 Aliases**:
   - Documented alias mapping for C4 tasks (`items.minItems`, `items.required`, `items.sku.pattern`) without modifying raw files.
   - TF-IDF and LSA/TruncatedSVD evaluated deterministically at $k \in \{1, 2, 3, 5\}$ matching diagnostic targets:
     - TF-IDF: $k=1$ (10.94%, 24/32 zero), $k=2$ (15.62%, 21/32 zero), $k=3$ (27.08%, 15/32 zero), $k=5$ (30.21%, 13/32 zero).
     - LSA: $k=1$ (9.90%, 25/32 zero), $k=2$ (16.15%, 21/32 zero), $k=3$ (24.48%, 17/32 zero), $k=5$ (35.42%, 12/32 zero).
5. **Hypothesis H1 Robustness & Unit of Analysis Disclosure**:
   - Monte Carlo one-sided paired sign-flip permutation test ($B=10,000$, seed $42$) with valid plus-one correction ($p = (0+1)/(10001) \approx 0.0001$, $p < 0.001$).
   - Four-cluster sensitivity analysis disclosure ($p = 2/16 = 0.125$) confirming task-level significance reflects template-family recurrence.
6. **Cross-Schema Epistemic & Semantic Clarification**:
   - Corrected pooled token accounting note to $54,657 \rightarrow 42,369$ tokens (22.5% pooled savings) across the 64 per-task records.
   - Distinguishes 4-domain macro savings (22.3%, unrounded 22.3355%) and 3-new-domain macro savings (22.7%, unrounded 22.691%) from pooled aggregate (22.5%).
   - Disambiguates Invariant Floor ($C_I^*$, macro 316.8) from Mean Initial $S_0$ (macro 361.3).
   - Accurately described study as a deterministic simulation-based mechanism stress test with heuristic token counts; live API calls are restricted to the primary benchmark.
7. **Empirical Latency Hierarchy**:
   - Request-level model turnaround: $p_{50}=3,407.11\text{ ms}$, $p_{90}=14,737.95\text{ ms}$, $p_{99}=56,708.45\text{ ms}$, mean$=7,752.79\text{ ms}$ (556 traces).
   - Local AST pipeline latency: $p_{50}=20.1\ \mu\text{s}$, $p_{99}=46.1\ \mu\text{s}$, ratio $= 0.00059\%$ of request $p_{50}$.
   - Simulated task trajectory turnaround estimate: $p_{50}=9,594.12\text{ ms}$ (Monte Carlo bootstrap, seed=42, 10,000 iterations).
8. **Manuscript & Paper Table Synchronization**:
   - Tables I, II, III, IV generated strictly into `version_2/paper_v2/tables/` via `generate_paper_tables_v2.py`.
   - Dynamic Initial $S_0$ and Reactive Expansion $\Delta S$ derivation and exact McNemar $p$-values ($p = 0.0078125$). Structural lift for $k=1$ reactive vs Full standardized to $+6.3\text{ pp}$ ($6.25\%$, round-half-up).
   - First-pass structural rate standardized to `31.3%` ($10/32 = 31.25\%$, round-half-up) across LaTeX, CSV, and JSON.
   - Statistical test reporting for Hypothesis H1 synchronized: $\Delta F_1 = +0.613$ (unrounded $+0.6125$, 95% CI $[+0.419, +0.781]$, permutation $p < 0.001$).
   - H3 causal phrasing softened; PDF compilation status documented as `BLOCKED` due to missing `pdflatex` in Windows OS environment; LaTeX source trees are verified, lint-clean, and in-sync.
9. **Detached Sidecar Attestation**:
   - Release attestation is generated strictly external to the archive (`.attestation.json` and `.attestation.md`) after performing clean-extraction verification on a fresh temporary directory. The release archive is never modified after computing its final hash.

---

## 2. Inventory of New & Hardened Release Files

| File | Type | Description |
| :--- | :--- | :--- |
| `version_2/RELEASE_VERSION` | Text | Single source of truth version string (`2.0.3`) |
| `version_2/reconcile_canonical_metrics.py` | Python Script | Canonical derivation and pure read-only `--check` auditing |
| `version_2/canonical_metrics.json` | JSON Artifact | Authoritative metric repository derived from frozen evidence |
| `version_2/derive_cross_schema_metrics.py` | Python Script | Read-only in-memory derivation tool for 64 cross-schema records |
| `version_2/cross_schema_derived_summary.json` | JSON Artifact | Recomputed summary for Table IV |
| `version_2/run_dense_rag_baseline.py` | Python Script | Diagnostic retrieval curve evaluator ($k \in \{1, 2, 3, 5\}$) |
| `version_2/dense_rag_evaluation.json` | JSON Artifact | Structured retrieval curve outputs |
| `version_2/retrieval_evaluation_curve.csv` | CSV Artifact | Tabular retrieval curve for paper and auditing |
| `version_2/generate_paper_tables_v2.py` | Python Script | Programmatic generator for paper Tables I, II, III, IV |
| `version_2/verify_version_2_integrity.py` | Python Script | Hardened 9-check verifier with structured error handling |
| `version_2/test_verifier_regressions.py` | Python Test | 31-part verifier failure-mode and regression test suite |
| `version_2/test_packaging_behavior.py` | Python Test | Behavioral packaging and omission test suite |
| `create_audit_zip.py` | Python Script | Production archive packager and validator with duplicate/traversal guards |
| `requirements-audit.txt` | Dependencies | Pinned dependencies (`numpy==2.2.2`, `scikit-learn==1.9.1`) |
| `version_2/baseline_comparison_snapshot.json` | JSON Artifact | Multi-arm comparative systems evaluation data |
| `version_2/paper_v2/tables/table1_systems_evaluation.tex` | LaTeX Table | Table I multi-arm systems evaluation |
| `version_2/paper_v2/tables/table2_latency_breakdown.tex` | LaTeX Table | Table II local AST vs request turnaround latency |
| `version_2/paper_v2/tables/table3_retrieval_baseline.tex` | LaTeX Table | Table III diagnostic retrieval curve |
| `version_2/paper_v2/tables/table4_cross_schema.tex` | LaTeX Table | Table IV showing Floor $C_I^*$, Mean $S_0$, and corrected 54,657 -> 42,369 note |
| `version_2/paper_v2/sections/00_abstract.tex` | LaTeX Section | Abstract with synchronized H1 $\Delta F_1 = +0.613$ |
| `version_2/paper_v2/sections/01_introduction.tex` | LaTeX Section | Intro with synchronized H1 $\Delta F_1 = +0.613$ |
| `version_2/paper_v2/sections/03_experimental_setup.tex` | LaTeX Section | Honest provenance and H1 vocabulary overlap / feature split |
| `version_2/paper_v2/sections/04_results.tex` | LaTeX Section | Results with 31.3% first-pass structural rate and retrieval table |
| `version_2/paper_v2/sections/05_cross_schema_results.tex` | LaTeX Section | Reframed as simulation-based stress test with heuristic tokens |
| `version_2/paper_v2/sections/07_discussion.tex` | LaTeX Section | Scoped epistemological boundaries between primary and cross-schema studies |
| `version_2/CHANGELOG.md` | Markdown | Comprehensive release history |
| `version_2/README_V2.md` | Markdown | Updated documentation with relative links |
