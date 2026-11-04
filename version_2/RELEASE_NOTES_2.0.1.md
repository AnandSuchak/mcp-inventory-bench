# Release Notes: LASR-MCP Version 2.0.1 Controlled Patch

**Release Version:** 2.0.1  
**Baseline Version:** 2.0.0 (`lasr_v2_audit_bundle.zip`, SHA-256: `36cf1def3de7bde589c02839b26ed10ac0fb2ec923eaffb46282e96e43fd00f3`)  
**Release Date:** 2026-10-16  
**Author:** Anand S. Suchak  
**Scope:** Packaging defect remediation and verifier error-handling hardening. No benchmark data, research metrics, or scientific conclusions have been modified.

---

## 1. Executive Summary

Version 2.0.1 is a controlled maintenance patch addressing the standalone verification and archive reproducibility defect identified in Version 2.0.0.

In Version 2.0.0, running `verify_version_2_integrity.py` within a freshly extracted release archive raised an uncaught `FileNotFoundError` during Check 9 because `create_audit_zip.py` was not packaged at the root of the archive. Furthermore, missing files caused uncaught exceptions instead of structured audit failures.

Version 2.0.1 resolves these issues:
1. `create_audit_zip.py` is now packaged at the archive root.
2. `create_audit_zip.py` explicitly excludes all `*.zip` files and temporary folders to guarantee no recursive archive nesting.
3. `verify_version_2_integrity.py` features robust file-existence checks, producing actionable failure diagnostics instead of crashing.
4. `verification_audit_certificate.json` is exported unconditionally with dynamic runtime timestamps and complete check details.

---

## 2. Scope & Invariant Preservation

- **Benchmark Invariants**: The 32 frozen primary tasks, 556 provider execution traces, and 64 cross-schema validation records remain **byte-for-byte identical** to the baseline.
- **Scientific Metrics**: Token accounting (Full: 96,629, Reactive $k=2$: 75,248; 22.1% workload savings), empirical latency ($p_{50} = 3,407.1\text{ ms}$, AST $p_{50} = 20.1\ \mu\text{s}$), and retrieval recall (TF-IDF 12.5%, Inductive LSA 14.1%) are strictly preserved.
- **Version 1 Immutability**: All original Version 1 files (`paper/main.pdf`, `paper/`, `datasets/`, `trace/`, `README.md`) remain untouched.

---

## 3. Verification Test Results

| Test # | Test Description | Condition | Result | Details |
| :---: | :--- | :--- | :---: | :--- |
| **T1** | Absent Packaging Script Handling | `create_audit_zip.py` removed | **PASS** | Verifier completed cleanly without exception; Check 9 failed; failure certificate written with status `CHECKS_FAILED`; exit code 1. |
| **T2** | Standard Verification Execution | Workspace with all files | **PASS** | All 9 checks passed with 100% precision; exit code 0; certificate written with status `ALL_CHECKS_PASSED`. |
| **T3** | Bundle Generation & File Inclusions | Run `create_audit_zip.py` | **PASS** | Generated `lasr_v2_audit_bundle_v2.0.1.zip` (628 files); contains `create_audit_zip.py` at root; excludes all `*.zip`. |
| **T4** | Clean-Directory Independent Extraction | Extract to isolated temp folder | **PASS** | Extracted bundle into clean temp folder; ran `verify_version_2_integrity.py`; all 9 checks passed; certificate validated. |
| **T5** | Manuscript LaTeX Compilation | `pdflatex main_v2.tex` | **BLOCKED** | LaTeX toolchain not installed on host PATH; documented build command preserved. |

---

## 4. Release Artifacts

- **Primary Archive**: `lasr_v2_audit_bundle_v2.0.1.zip`
- **Audit Verifier**: `version_2/verify_version_2_integrity.py`
- **Audit Certificate**: `version_2/verification_audit_certificate.json`
- **Changelog**: `version_2/CHANGELOG.md`
- **Release Notes**: `version_2/RELEASE_NOTES_2.0.1.md`
