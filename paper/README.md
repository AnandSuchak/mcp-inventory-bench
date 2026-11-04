# LASR-MCP: Historical Manuscript Archive (Version 1.0)

> **Notice: Historical Archive Only**  
> The contents of this directory (`paper/`) represent the **historical 8-page preliminary manuscript** (Version 1.0 / September 2026), evaluated on preliminary single-trial runs.  
>  
> The authoritative, publication-ready **15-page IEEE manuscript (Version 2.0.3)** is located in:  
> [`version_2/paper_v2/`](../version_2/paper_v2/)  
>  
> Canonical 15-page PDF:  
> [`version_2/paper_v2/main_v2.pdf`](../version_2/paper_v2/main_v2.pdf) (SHA-256: `73e1b92e1308b57c5760f3b9ef0a2d82355daa1858227a263eca36c0fcece82d`)

---

## Historical Version 1.0 Overview

- **Format:** IEEE Conference 2-column format (Exact 8.0 pages).
- **Driver:** [`paper/main.tex`](main.tex).
- **Rendered PDF:** [`paper/main.pdf`](main.pdf) (143,557 bytes, 27 embedded fonts).
- **Scope:** Preliminary 32-task exploration that utilized offline heuristic schema estimates.

## Canonical Version 2.0.3 Differences

The updated Version 2.0.3 manuscript incorporates:
1. **P+C Token Accounting:** Eliminates heuristic schema double-counting by taking provider-reported `promptTokenCount + candidatesTokenCount` directly from `usageMetadata` across 7,860 live Gemini API calls.
2. **Empirical Retry-Amortization Boundary:** Discloses that while LASR $k=2$ achieves 13.5% token savings in routine cluster C1, multi-turn retry cascades incur a +25.94% overall workload penalty across clusters C2–C4 relative to Full Schema Control.
3. **Full 15-Page Scope:** Complete theoretical proofs of finite monotonic convergence, per-cluster bootstrap confidence intervals, and detailed failure diagnostics.

Please refer to [`version_2/paper_v2/`](../version_2/paper_v2/) for all current research and publication artifacts.
