# LASR-MCP Release Notes — Version 2.0.3

**Release Version:** `2.0.3`  
**Date:** November 2026  
**Author:** Anand S. Suchak (Independent Researcher)  
**Repository:** [https://github.com/AnandSuchak/mcp-inventory-bench](https://github.com/AnandSuchak/mcp-inventory-bench)  
**Publication:** *LASR-MCP: Learned Adaptive Schema Resolution with Dynamic In-Tree Recovery for Enterprise Tool-Calling Agents*  

---

## 1. Release Overview

LASR-MCP Version 2.0.3 is the definitive publication-ready release of the LASR-MCP replication package and manuscript. It supersedes preliminary Version 1.0 evaluations by correcting token accounting methodologies, providing full transparency on the multi-turn economics of agentic retry cascades, and presenting an audited, fixed-seed canonical live benchmark of $N=3,840$ trials across 32 tasks and six experimental arms.

---

## 2. Key Scientific & Architectural Updates

### A. Corrected Token Accounting (Provider-Reported P+C)
- **Elimination of Heuristic Double-Counting:** Preliminary evaluations (v1.0) added offline schema estimates ($S_0, \Delta S$) to provider prompt tokens. Because provider prompt tokens already encompass the complete serialized MCP tool declaration, this resulted in token double-counting.
- **Canonical Metric:** Version 2.0.3 adopts provider-reported prompt-plus-candidate tokens directly from `usageMetadata`:
  $$\text{Recorded P+C} = \text{promptTokenCount} + \text{candidatesTokenCount}$$
  This equals `totalTokenCount` across all 7,860 response-bearing calls in our audited telemetry (zero thinking tokens, zero client-side tool prompts).
- **Historical Integrity:** All historical datasets (Scope 1) and raw trial traces remain preserved byte-for-byte; no historical records were altered or deleted.

### B. The Retry-Amortization Boundary & Honest Economic Reporting
- **Benchmark-Wide Result:** Proposed LASR $k=2$ reactive uses **$31.65\%$ fewer tokens than the zero-constraint floor** baseline (`ci_k0`), but incurs a **$+25.94\%$ overall token workload penalty** compared to Full Schema Control across the complete 3,840-trial benchmark (95% CI: $[-52.55\%, -3.16\%]$).
- **Cluster-Specific Regimes:**
  - **Routine Cluster C1 (`routine_regional_replenish`):** Achieves **$13.49\%$ lower token consumption** than Full Schema Control ($847.6$ vs. $979.8$ tokens/trial) with **$100.0\%$ structural reliability**.
  - **Complex Clusters C2–C4:** When constraint violations necessitate multi-turn retries, the cumulative cost of resending conversational history rapidly exceeds the upfront savings of a pruned schema.
- **Scientific Takeaway:** The paper demonstrates that adaptive schema pruning is highly effective for predictable, routine tasks, but monolithic full schemas remain economically optimal when tasks frequently trigger multi-turn retry cascades.

### C. 15-Page IEEE Transactions-Scope Manuscript
- Expanded from the preliminary 8-page conference draft to a comprehensive 15.0-page IEEE manuscript ([`version_2/paper_v2/main_v2.pdf`](../../version_2/paper_v2/main_v2.pdf)).
- Contains formal proofs of finite monotonic recovery, 10,000-resample paired cluster bootstrap statistics, and exhaustive ablation across six experimental arms.

---

## 3. Publication & Distribution Artifacts

| Artifact | File Name | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **Authoritative Manuscript** | `LASR_MCP_v2.0.3_Manuscript.pdf` | 525 KB | `73e1b92e1308b57c5760f3b9ef0a2d82355daa1858227a263eca36c0fcece82d` |
| **LaTeX Source Bundle** | `lasr_v2_203_manuscript_bundle.zip` | 844 KB | `ae9599564b55a5e19004f32ded7c91fe2b46c480b12914b5343834bcf789044f` |
| **Raw Live Telemetry** | `lasr_v2_203_raw_benchmark_telemetry.zip` | 4.3 MB | `9ee32f32dd332c06b978c4dc37482eebba95216a131961adbbb742b1d1c23b90` |
| **Verification Manifest** | `release/v2.0.3/MANIFEST.sha256` | 1.1 KB | — |

---

## 4. Test Suite & Verification Status

- **Total Test Suite:** 110 passed (74 core framework tests + 36 verifier regression tests).
- **Read-Only Canonical Audit:** `python version_2/reconcile_canonical_metrics.py --check` passes with zero discrepancies against raw evidence.
- **LaTeX Compilation:** Exact 15.0 pages with zero overfull `\hbox` warnings.
