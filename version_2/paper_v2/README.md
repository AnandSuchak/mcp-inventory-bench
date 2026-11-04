# LASR-MCP IEEE Manuscript Source & Build Package (Version 2.0.3)

**Manuscript Title**: LASR-MCP: Learned Adaptive Schema Resolution with Dynamic In-Tree Recovery for Enterprise Tool-Calling Agents  
**Author**: Anand S. Suchak (anand02suchak@gmail.com)  
**Target Venue**: IEEE Transactions on Knowledge and Data Engineering / IEEE Conference Format  
**Version**: 2.0.3  

---

## 1. Prerequisites & Build Tools

To compile the manuscript from source, ensure you have a standard LaTeX distribution installed (e.g., TeX Live $\ge 2023$, MacTeX, or TinyTeX):
- `pdflatex` (pdfTeX $\ge 1.40$)
- `bibtex` (BibTeX $\ge 0.99$)

### Included Style Files & Classes
This package includes all non-standard document classes and bibliography styles:
- `IEEEtran.cls`: Official IEEE LaTeX document class (version 1.8b).
- `IEEEtran.bst`: Official IEEE bibliography style.

---

## 2. Compilation Sequence

From the root of this unpacked bundle directory, execute the standard 4-pass compilation sequence:

```bash
pdflatex -interaction=nonstopmode main_v2.tex
bibtex main_v2
pdflatex -interaction=nonstopmode main_v2.tex
pdflatex -interaction=nonstopmode main_v2.tex
```

This sequence:
1. Generates the initial `.aux` file with citation and cross-reference keys.
2. Invokes BibTeX to generate `main_v2.bbl` from `references.bib` using `IEEEtran.bst`.
3. Resolves bibliography citations and cross-references into `.aux`.
4. Produces the final, camera-ready `main_v2.pdf` with all citations and references resolved.

---

## 3. Package Structure

```
├── main_v2.tex                  # Primary LaTeX driver file
├── main_v2.pdf                  # Camera-ready compiled PDF manuscript
├── IEEEtran.cls                 # IEEE class file
├── IEEEtran.bst                 # IEEE BibTeX style file
├── references.bib               # Complete bibliography database
├── README.md                    # Build instructions & metric definitions
├── MANIFEST.sha256              # Cryptographic checksums of bundled sources
├── sections/                    # Modular LaTeX section sources
│   ├── 00_abstract.tex
│   ├── 01_introduction.tex
│   ├── 02_system_architecture.tex
│   ├── 03_experimental_setup.tex
│   ├── 04_results.tex
│   ├── 05_cross_schema_results.tex
│   ├── 06_related_work.tex
│   └── 07_discussion.tex
├── tables/                      # LaTeX table sources (programmatically verified)
│   ├── table1_systems_evaluation.tex
│   ├── table2_paired_bootstrap.tex
│   ├── table3_cluster_breakdown.tex
│   └── table4_cross_schema.tex
└── figures/                     # Vector graphics and TikZ diagrams
    ├── fig1_system_architecture.tex
    ├── fig2_systems_evaluation.pdf
    └── fig3_cluster_breakdown.pdf
```

---

## 4. Metric Definitions & Accounting Rules

All empirical claims reported in this manuscript strictly follow these formalized accounting rules:

1. **Recorded P+C Tokens**: The primary economic workload metric, defined as `promptTokenCount` + `candidatesTokenCount` as reported directly in provider `usageMetadata` (Google Generative Language API). To prevent double-counting, offline heuristic schema token sizes ($S_0, \Delta S$) are never added to provider prompt tokens.
2. **Tokens-to-Success ($TTS_{\text{P+C}}$)**: Cumulative recorded prompt-plus-candidate tokens consumed across all attempts for structurally successful trajectories ($N_{\text{succ}}$).
3. **First-Pass Hierarchical Success**: A strict conjunction ($\text{Structural} \land \text{Semantic}$) requiring the model's initial Attempt 1 generation to satisfy both JSON Schema Draft 2020-12 constraints and domain business logic.
4. **Final Structural Reliability**: The percentage of trajectories that satisfy JSON Schema validation within the 3-attempt execution budget.
5. **Final Semantic Correctness**: The percentage of trajectories that satisfy exact domain logic within the execution budget.
6. **Retry-Amortization Boundary**:
   - In routine regimes ($C_1$, $M \le k$), prioritized upfront bundling ($k=2$) achieves 75.0% first-pass success and delivers approximately **13.5% lower P+C token usage** ($847.6$ vs.\ $979.8$ tokens) at 100.0% reliability.
   - In deep inter-field constraint regimes ($C_2$--$C_4$, $M > k$), single-tool isolation favors monolithic Full Control by avoiding multi-turn retry cascades ($1,116.8$ vs.\ $1,406.5$ tokens overall; LASR $k=2$ overall workload is approximately **25.94% higher** than Full Control's across all 32 tasks).
