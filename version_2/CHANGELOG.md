# Changelog: LASR-MCP Version 2

All notable changes to the LASR-MCP Version 2 benchmark, audit tools, and manuscripts are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to Semantic Versioning for its release packaging. Note that release versions track software/audit releases and are kept separate from scientific manuscript version designations.

---

## [2.0.3-rebuilt-candidate] - 2026-10-26

### Added
- **Full-Scale Empirical Benchmark Reconciliation ($N=3,840$ Trials)**: Reconciled complete 20-repetition live benchmark on `gemini-3.5-flash-lite` across 32 tasks and 6 experimental arms (7,860 response-bearing provider calls, 154 client transport retries, ₹116.16 total prepayment credit spend).
- **Retry-Amortization Boundary Formalization**: Added break-even proof and empirical demonstration showing LASR $k=2$ achieves $+13.5\%$ net token savings in routine domains ($C_1$, $847.6$ vs.\ $979.8$ tokens) at $100.0\%$ structural reliability, while monolithic schemas remain optimal in complex single-tool tasks ($C_2$--$C_4$) where multi-turn retry re-transmission dominates.
- **Deterministic IEEE Vector Figures**: Added Figure 1 (system architecture in native `TikZ`), Figure 2 (systems evaluation bar chart with dual-axis success rates), and Figure 3 (cluster break-even comparison) exported strictly as vector PDFs directly from raw telemetry.
- **Percentile Bootstrap Clarification**: Corrected bootstrap terminology in `version_2/analyze_fresh_benchmark.py` and across all documentation to "paired task-cluster percentile bootstrap (10,000 resamples, seed=42)".
- **IEEE Generative AI Compliance**: Inserted formal Generative AI Disclosure statement and finalized Abstract and Conclusion matching verified archive evidence.

---

## [2.0.3] - 2026-10-20

### Added
- **Single Source of Versioning**: Maintained `version_2/RELEASE_VERSION` containing `2.0.3` as the authoritative version reference across builder, verifier, reconciler, and attestations, failing closed if missing or empty.
- **Baseline Manifest Preservation & Independent Metadata Validation**: Restored `datasets/frozen_benchmark_n32/MANIFEST.sha256` byte-for-byte to baseline Version 2.0.0 hash `71e87aeefc5b10f7b5bc99571ecaf430b24b9f1811fa4dd3d47af50e84951c0b` (listing only `invariant_optimization_summary.json`); independently validates `metadata.json` via pinned hash `ab8ca76d5ef4...`.
- **Dynamic Table I Generation (`version_2/generate_paper_tables_v2.py`)**: Dynamically computes Initial $S_0$ and Reactive Expansion $\Delta S$ from per-task optimization records (Full: 552.0 / 0.0; $C_I^*$: 339.0 / 0.0; $k=1$ static: 361.1 / 0.0; $k=1$ reactive: 361.1 / 45.4; $k=2$ reactive: 366.8 / 43.8; Oracle: 359.0 / 48.3). Standardized Full Schema first-pass structural percentage to $10/32 = 31.25\% \to 31.3\%$ (round-half-up).
- **Dynamic Table II Statistical Tests**: Dynamically computes exact one-sided McNemar / binomial $p$-values ($p = 0.0078125$ for LASR reactive arms over static control). Standardized structural lift for $k=1$ reactive vs Full to $2/32 = 6.25\% \to +6.3\text{ pp}$ under consistent round-half-up policy.
- **H1 Predictor Statistical Robustness & Real Provenance Hashes (`version_2/reproduce_h1_predictor.py`)**: Implemented Monte Carlo one-sided paired sign-flip permutation test ($B=10,000$, seed $42$) with valid plus-one correction ($p = (0+1)/(10001) \approx 0.0001$, $p < 0.001$). Added transparent 4-cluster sensitivity analysis disclosure ($p = 2/16 = 0.125$). Replaced circular hash with real source hashes (`trace/paraphraser.py`, `trace/predictor.py`, `version_2/reproduce_h1_predictor.py`, and `invariant_optimization_summary.json`).
- **Gold-Label Alias Normalization & Protocol Documentation (`version_2/run_dense_rag_baseline.py`)**: Documented query-inclusive/transductive TF-IDF and inductive LSA protocols explicitly. Derived `top_2_retrieved_chunk_tokens_mean` from retrieved chunks while preserving historical active-ledger exposure `top_2_injected_tokens_mean: 64.5`.
- **Comprehensive 31-Test Verifier Regression Suite (`version_2/test_verifier_regressions.py`)**: Added dedicated negative tests for Table III C1 cell tampering (87.5% -> 7.5%), frozen manifest integrity tampering, metadata tampering, CLI script `--help` and dry-run immutability across all 5 companions, and RELEASE_VERSION fail-closed verification.
- **Protected Release Archives**: Added historical candidates `lasr_v2_audit_bundle_v2.0.3.zip` (`22183ed4...`), `lasr_v2_203_closure_candidate.zip` (`d43c20a7...`), and `lasr_v2_203_final_candidate.zip` (`811bd186...`) to `PROTECTED_RELEASES` in `create_audit_zip.py`, packaging the reconciled candidate as `lasr_v2_203_reconciled_candidate.zip`.
- **Metric Reconciliation & Prompt-Plus-Candidate Formulation**: Defined canonical primary token metric strictly as provider-recorded prompt-plus-candidate token subtotal ($\text{prompt\_tokens} + \text{completion\_tokens}$, Full: 61,853; $k=1$: 51,594; $k=2$: 50,276), eliminating heuristic schema double-counting.
- **Hierarchical First-Pass Success**: Defined first-pass hierarchical success as $\text{first\_pass\_structural} \land \text{first\_pass\_semantic}$ (Full: 10/32; $k=1$: 5/32; $k=2$: 6/32).
- **Exploratory Live Replication & Sensitivity Analysis**: Integrated exploratory live replication results (285 unique live API entries + within-run cache reuse, live P+C savings point estimates: 5.69% for $k=1$, 7.79% for $k=2$, with paired bootstrap intervals crossing zero).

### Fixed
- **Harden Table Verification**: Upgraded reconciler and verifiers to compare shipped `.tex` tables byte-for-byte / cell-by-cell against deterministic in-memory generator, preventing isolated cell tampering from going undetected.
- **CLI Script Safe Dry-Run Defaults**: Configured all script entry points (`generate_paper_tables_v2.py`, `langgraph_evaluator.py`, `run_dense_rag_baseline.py`, `reproduce_h1_predictor.py`, `derive_cross_schema_metrics.py`) to honor `--help` and default to safe dry-run in-memory evaluation without modifying disk files.
- **Hypothesis H3 Phrasing Softened**: Replaced causal assertions with exact statistical characterizations across Abstract, Introduction, and Results sections ($p=0.0078125$, cluster sensitivity $p=0.125$).
- **Path Portability**: Replaced machine-specific absolute paths in `lasr_trace_audit_report.json` with relative path `"."` and explicitly designated as `HISTORICAL_PRE_ALIAS_AUDIT_SNAPSHOT`.
- **Documentation Distinction**: Added clear demarcation between repository orchestration worktree and canonical packaged audit bundle in `version_2/README_V2.md`.

---

## [2.0.2] - 2026-10-16

### Added
- **Direct Manifest Validation (Check 1)**: Implemented an active parser and integrity checker for both `MANIFEST.sha256` files (`datasets/frozen_benchmark_n32/MANIFEST.sha256` and `datasets/cross_schema_validation/MANIFEST.sha256`). Rejects malformed lines, missing files, and hash mismatches while retaining independently pinned trusted hashes (`78c2c88e...` and `b3d57636...`) to prevent manifest tampering.
- **Behavioral Packaging Verification (Check 9)**: Upgraded Check 9 from static string-searching to an active behavioral packaging test. The verifier now executes `create_audit_zip.py` into a controlled temporary directory, inspects the generated zip, and verifies the presence of root `create_audit_zip.py`, Version 2 tree, frozen datasets, cross-schema datasets, exactly 556 cache traces, and trace sources.
- **Behavioral & Negative Test Suite (`version_2/test_packaging_behavior.py`)**: Created an automated test suite verifying that Check 9 detects and rejects omitted source trees even if the packager script still contains the folder name as a string.
- **Audit Stage Identification & Release Attestation**: Added `--stage` flag to `verify_version_2_integrity.py` distinguishing `pre_packaging_audit` from `clean_extraction_verification`. Created standalone post-package release attestation (`version_2/RELEASE_ATTESTATION_2.0.2.md` and `version_2/release_attestation_v2.0.2.json`).
- **LaTeX Transient Build Artifact Policy**: Explicitly configured `create_audit_zip.py` to filter transient files (`.aux`, `.log`, `.fls`, `.out`, `.fdb_latexmk`, `.bbl`, `.blg`, `.synctex.gz`, `.toc`), preventing archive drift from local compilation passes.

### Fixed
- **Math Mode Font Command**: Removed misplaced `\small` text font command from inside `\begin{equation}` in `version_2/paper_v2/sections/02_system_architecture.tex`, resolving LaTeX font warnings in math mode.
- **SHA-256 Overfull Line**: Wrapped the 64-character SHA-256 hash in `version_2/paper_v2/sections/03_experimental_setup.tex` across two balanced lines, preventing gutter intrusion and column overflow.
- **Table I Overfull Width**: Wrapped `version_2/paper_v2/tables/table1_systems_evaluation.tex` in `\resizebox{\textwidth}{!}` with a separated minipage footnote note, eliminating overfull horizontal box warnings.

### Changed Files
1. `create_audit_zip.py`:
   - Updated default output to `lasr_v2_audit_bundle_v2.0.2.zip`.
   - Added `LATEX_TRANSIENT_EXTS` exclusion policy (`.aux`, `.log`, `.fls`, `.out`, etc.).
   - Added support for absolute and relative paths via `--out`.
2. `version_2/verify_version_2_integrity.py`:
   - Check 1: Added `parse_and_validate_manifest` to parse and verify `MANIFEST.sha256` files directly against disk files, alongside trusted pinned hashes.
   - Check 8: Added validation of math mode `\small` removal, SHA-256 wrapping, and Table I resizebox.
   - Check 9: Replaced string matching with dynamic behavioral packaging test in controlled temp directory, verifying 556 cache traces, root packager, zero nested zips, and zero transient files.
   - Added `--stage` parameter and factual reporting.
3. `version_2/paper_v2/sections/02_system_architecture.tex`:
   - Removed `\small` inside equation (38).
4. `version_2/paper_v2/sections/03_experimental_setup.tex`:
   - Formatted cryptographic provenance hash to fit single column width.
5. `version_2/paper_v2/tables/table1_systems_evaluation.tex`:
   - Added `\resizebox{\textwidth}{!}` and separated footnote note.
6. `version_2/test_packaging_behavior.py`:
   - Added test suite for behavioral packaging and negative omission detection.
7. `version_2/CHANGELOG.md`:
   - Added Version 2.0.2 entry.
8. `version_2/RELEASE_NOTES_2.0.2.md`:
   - Created release notes for Version 2.0.2.
9. `version_2/README_V2.md`:
   - Updated inventory and documentation for Version 2.0.2.

---

## [2.0.1] - 2026-10-16

### Fixed
- **Reproducible Archive Verification Defect (Check 9)**: Resolved an issue where running `verify_version_2_integrity.py` inside a freshly extracted release archive crashed with an uncaught `FileNotFoundError` because `create_audit_zip.py` had not been included in the root of the generated zip bundle.
- **Archive Self-Inclusion**: Enhanced `create_audit_zip.py` to explicitly exclude all `*.zip` files and temporary extraction directories (`temp_*`, `test_*`, `tmp/`), preventing accidental recursive zip-in-zip bloat.
- **Graceful Error Handling in Verifier**: Updated `version_2/verify_version_2_integrity.py` so that missing files across all 9 checks produce structured failure reports (`passed: false` with actionable diagnostic messages) rather than unhandled Python exceptions.
- **Unconditional Audit Certificate Generation**: Guaranteed that `version_2/verification_audit_certificate.json` is exported even when checks fail, recording exact passed/failed check counts and failure details.
- **Dynamic Runtime Timestamp**: Replaced hardcoded historical timestamp with runtime ISO 8601 timestamp (`datetime.now(timezone.utc).astimezone().isoformat()`).

### Changed Files
1. `create_audit_zip.py`:
   - Added `create_audit_zip.py` to `include_paths` with root arcname.
   - Added `*.zip` filtering and temporary directory exclusion during walk.
   - Added `--out` command line argument, defaulting to `lasr_v2_audit_bundle_v2.0.1.zip`.
2. `version_2/verify_version_2_integrity.py`:
   - Updated Check 9 to verify existence of `create_audit_zip.py` at workspace root, inclusion of all 5 source trees (`version_2`, `datasets/frozen_benchmark_n32`, `datasets/cross_schema_validation`, `datasets/cache`, `trace`), self-inclusion, and `.zip` exclusion.
   - Guarded Checks 1–8 with file existence validations and descriptive error details.
   - Replaced static timestamp with dynamic runtime timestamp.
   - Added release version tag `2.0.1` to exported certificate.
3. `version_2/README_V2.md`:
   - Documented Version 2.0.1 controlled patch and updated file inventory.
4. `version_2/CHANGELOG.md`:
   - Created this changelog documenting 2.0.0 baseline and 2.0.1 patch.
5. `version_2/RELEASE_NOTES_2.0.1.md`:
   - Published release notes for Version 2.0.1.

---

## [2.0.0] - 2026-10-16

### Baseline Snapshot
- **Baseline Archive**: `lasr_v2_audit_bundle.zip` (SHA-256: `36cf1def3de7bde589c02839b26ed10ac0fb2ec923eaffb46282e96e43fd00f3`).
- **Mathematical Bound Correction**: Proved finite monotonic recovery bound $K \le M - |A_0|$ in `version_2/formal_termination_proof.tex` and `version_2/paper_v2/sections/02_system_architecture.tex`. Disproved heuristic depth bound $K \le D$ via sibling-leaf counterexample.
- **LaTeX Proof Environment**: Defined `\begin{IEEEproof}` environments compliant with `IEEEtran.cls`.
- **Table Formatting Fixes**: Resolved Table V single-column overflow using `\resizebox{\columnwidth}{!}` and replaced cross-schema pooled row schema sizes with `-- & --` in Table IV.
- **Retrieval Baselines Decoupling**: Recomputed Lexical TF-IDF Macro Recall@2 (12.5%, 75.0% zero-hits) and Inductive LSA SVD-16 Macro Recall@2 (14.06%, 71.9% zero-hits). Marked retrieval rows in Table V as `NOT MEASURED (Retrieval-Only)` to prevent conflation with end-to-end validator execution.
- **LangGraph Counterfactual Model**: Characterized LangGraph state accumulation as a trace-derived counterfactual token model (+45 tok compiler context, 103,895 tokens, +7.52% overhead / -7.52% net savings).
- **Latency Benchmarking**: Measured local in-tree AST recomposition latency across 1,000 iterations ($p_{50} = 20.1\ \mu\text{s}$) against 556 empirical API response traces ($p_{50} = 3,407.1\text{ ms}$), showing an overhead ratio of $0.00059\%$.
- **Version 1 Immutability**: All original Version 1 files (`paper/main.pdf`, `paper/`, `datasets/`, `trace/`, `README.md`) preserved 100% untouched.
