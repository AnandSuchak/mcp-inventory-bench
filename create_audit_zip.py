#!/usr/bin/env python3
"""
Bundle Creator & Production Validator for LASR-MCP Version 2.0.3 Audit Archive
Project: mcp-inventory-bench / Version 2.0.3
Author: Anand S. Suchak

Packages all Version 2.0.3 research artifacts into a deterministic, validated ZIP bundle:
- Packages candidate audit bundle (default: lasr_v2_203_final_candidate.zip)
- Builds to a temporary file, runs full production validation, and atomically moves to final destination.
- Refuses to overwrite released archives (e.g. 2.0.0, 2.0.1, 2.0.2, and prior 2.0.3 candidate).
- Fails closed if any required path is missing.
- Reusable validator: validate_audit_archive(zip_path).

Excludes:
- *.zip archives (preventing recursive self-inclusion)
- *.attestation.* sidecars (detached attestations remain outside archive)
- Transient LaTeX build artifacts: .aux, .log, .fls, .out, .fdb_latexmk, .bbl, .blg, .synctex.gz, .toc
- Python bytecode: __pycache__/, *.pyc, *.pyo
- VCS and virtual environments: .git/, .venv/, .pytest_cache/
- Temporary directories and test folders: tmp/, temp/, temp_*
"""

import os
import sys
import argparse
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

WORKSPACE = Path(__file__).resolve().parent

LATEX_TRANSIENT_EXTS = {
    ".aux", ".log", ".fls", ".out", ".fdb_latexmk",
    ".bbl", ".blg", ".synctex.gz", ".toc", ".lof", ".lot"
}

PROTECTED_RELEASES = {
    "lasr_v2_audit_bundle.zip",
    "lasr_v2_audit_bundle_v2.0.1.zip",
    "lasr_v2_audit_bundle_v2.0.2.zip",
    "lasr_v2_audit_bundle_v2.0.3.zip",
    "lasr_v2_203_closure_candidate.zip",
    "lasr_v2_203_final_candidate.zip",
    "lasr_v2_203_reconciled_candidate.zip",
    "lasr_v2_203_fresh_rerun_candidate.zip"
}

def get_release_version() -> str:
    v_file = WORKSPACE / "version_2" / "RELEASE_VERSION"
    if not v_file.exists():
        raise FileNotFoundError(f"Missing release version file: {v_file}")
    ver = v_file.read_text(encoding="utf-8").strip()
    if not ver:
        raise ValueError(f"Empty release version file: {v_file}")
    return ver

def validate_audit_archive(zip_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Reusable production validator for LASR-MCP audit archives.
    Inspects archive integrity, required members, exact trace counts, and exclusion rules.
    """
    if not zip_path.exists():
        return False, f"Archive file does not exist: {zip_path}", {}

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            corrupt = zf.testzip()
            if corrupt is not None:
                return False, f"Archive contains corrupt member: {corrupt}", {}

            namelist = zf.namelist()
            nameset = set(namelist)
            
            # Check duplicate member names (case-sensitive and normalized)
            if len(namelist) != len(nameset):
                return False, f"Archive contains duplicate member names ({len(namelist)} total, {len(nameset)} unique)", {}
            if len(namelist) != len(set(n.lower() for n in namelist)):
                return False, f"Archive contains case-colliding member names", {}

            # Prohibited: directory traversal or Windows backslashes
            invalid_paths = [n for n in namelist if ".." in n.split("/") or "\\" in n or n.startswith("/")]
            if invalid_paths:
                return False, f"Archive contains illegal path entries (traversal/absolute/backslash): {invalid_paths[:3]}", {}

            # Prohibited files: nested zip archives
            nested_zips = [n for n in namelist if n.lower().endswith(".zip")]
            if nested_zips:
                return False, f"Archive contains nested ZIP files: {nested_zips}", {}

            # Prohibited files: detached sidecars or stale in-package attestations
            sidecars = [n for n in namelist if ".attestation." in n.lower()]
            if sidecars:
                return False, f"Archive improperly includes detached attestation sidecars: {sidecars}", {}

            stale_attestations = [n for n in namelist if "release_attestation_2.0.2" in n.lower() or "release_attestation_v2.0.2" in n.lower()]
            if stale_attestations:
                return False, f"Archive contains stale in-package Version 2.0.2 attestations: {stale_attestations}", {}

            # Prohibited files: transient LaTeX build files
            transient_latex = [n for n in namelist if any(n.lower().endswith(ext) for ext in LATEX_TRANSIENT_EXTS)]
            if transient_latex:
                return False, f"Archive contains transient LaTeX build artifacts: {transient_latex[:3]}", {}

            # Prohibited files: bytecode or git/venv
            bytecode_or_git = [n for n in namelist if "__pycache__" in n or n.endswith(".pyc") or n.startswith(".git") or n.startswith(".venv")]
            if bytecode_or_git:
                return False, f"Archive contains bytecode or vcs artifacts: {bytecode_or_git[:3]}", {}

            # Required structural members
            required_members = [
                "create_audit_zip.py",
                "version_2/RELEASE_VERSION",
                "version_2/README_V2.md",
                "version_2/CHANGELOG.md",
                "version_2/RELEASE_NOTES_2.0.3.md",
                "version_2/verify_version_2_integrity.py",
                "version_2/reconcile_canonical_metrics.py",
                "version_2/canonical_metrics.json",
                "version_2/dense_rag_evaluation.json",
                "version_2/retrieval_evaluation_curve.csv",
                "version_2/derive_cross_schema_metrics.py",
                "version_2/cross_schema_derived_summary.json",
                "version_2/full_schema.json",
                "version_2/benchmark_tasks_n32.json",
                "version_2/langgraph_traces.json",
                "version_2/latency_benchmark_measurements.csv",
                "version_2/latency_benchmark_summary.json",
                "version_2/baseline_comparison_table.csv",
                "version_2/baseline_comparison_snapshot.json",
                "version_2/reproduce_h1_predictor.py",
                "version_2/h1_predictor_evaluation.json",
                "version_2/h1_predictor_evaluation.csv",
                "version_2/generate_paper_tables_v2.py",
                "version_2/paper_v2/tables/table1_systems_evaluation.tex",
                "version_2/paper_v2/tables/table2_paired_bootstrap.tex",
                "version_2/paper_v2/tables/table3_cluster_breakdown.tex",
                "version_2/paper_v2/tables/table4_cross_schema.tex",
                "version_2/paper_v2/sections/04_results.tex",
                "version_2/paper_v2/sections/05_cross_schema_results.tex",
                "datasets/frozen_benchmark_n32/invariant_optimization_summary.json",
                "datasets/frozen_benchmark_n32/metadata.json",
                "datasets/frozen_benchmark_n32/MANIFEST.sha256",
                "datasets/cross_schema_validation/cross_schema_results.json",
                "datasets/cross_schema_validation/MANIFEST.sha256",
                "version_2/test_verifier_regressions.py",
                "version_2/check_phase1_live_integrity.py",
                "version_2/audit_token_formulas.py",
                "version_2/check_telemetry_pilot.py",
                "trace/run_telemetry_pilot.py",
                "datasets/dataset_pilot_telemetry/pilot_summary.json",
                "datasets/dataset_pilot_telemetry/pilot_call_records.jsonl",
                "datasets/dataset_pilot_telemetry/pilot_manifest.json",
                "requirements-audit.txt"
            ]

            missing = [m for m in required_members if m not in nameset]
            if missing:
                return False, f"Archive missing {len(missing)} required members: {missing[:5]}", {}

            # Cache trace check (must be exactly 556 JSON traces)
            cache_traces = [n for n in namelist if n.startswith("datasets/cache/") and n.endswith(".json")]
            if len(cache_traces) != 556:
                return False, f"Expected 556 cache traces, found {len(cache_traces)}", {}

            stats = {
                "total_entries": len(namelist),
                "cache_traces": len(cache_traces),
                "uncompressed_bytes": sum(zf.getinfo(n).file_size for n in namelist),
                "compressed_bytes": sum(zf.getinfo(n).compress_size for n in namelist),
                "has_root_packager": "create_audit_zip.py" in nameset,
                "has_frozen_data": "datasets/frozen_benchmark_n32/invariant_optimization_summary.json" in nameset,
                "has_cross_data": "datasets/cross_schema_validation/cross_schema_results.json" in nameset
            }
            return True, f"Archive verified successfully ({len(namelist)} entries, 556 cache traces, 0 nested zips)", stats
    except Exception as exc:
        return False, f"Exception while validating archive {zip_path}: {exc}", {}

def make_audit_bundle(out_path: Optional[str] = None, allow_overwrite: bool = False) -> Path:
    version = get_release_version()
    if out_path is None:
        out_filename = "lasr_v2_203_fresh_rerun_candidate.zip"
    else:
        out_filename = out_path

    target = Path(out_filename)
    final_zip_path = target if target.is_absolute() else (WORKSPACE / target)

    # Refuse to overwrite released baseline archives
    if final_zip_path.name in PROTECTED_RELEASES:
        raise PermissionError(f"Refusing to overwrite protected baseline archive: {final_zip_path.name}")
    if final_zip_path.exists() and not allow_overwrite:
        raise FileExistsError(f"Target archive already exists: {final_zip_path}. Use another filename or remove old candidate.")

    include_paths = [
        "create_audit_zip.py",
        "version_2",
        "datasets/frozen_benchmark_n32",
        "datasets/cross_schema_validation",
        "datasets/cache",
        "datasets/dataset_pilot_telemetry",
        "trace",
        "requirements.txt",
        "requirements-audit.txt"
    ]

    if (WORKSPACE / "datasets" / "fresh_live_benchmark_n32").exists():
        include_paths.append("datasets/fresh_live_benchmark_n32")

    # Verify required root sources exist before building
    for item in include_paths:
        p = WORKSPACE / item
        if not p.exists():
            raise FileNotFoundError(f"Required path for packaging missing: {item}")

    print(f"Creating candidate audit zip for Version {version}...")

    # Build into a temporary zip file first
    temp_fd, temp_zip_str = tempfile.mkstemp(prefix="lasr_packager_tmp_", suffix=".zip")
    os.close(temp_fd)
    temp_zip_path = Path(temp_zip_str)

    try:
        file_count = 0
        total_bytes = 0

        with zipfile.ZipFile(temp_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for item in include_paths:
                p = WORKSPACE / item
                if p.is_file():
                    lower_name = p.name.lower()
                    if lower_name.endswith(".zip") or ".attestation." in lower_name or any(lower_name.endswith(ext) for ext in LATEX_TRANSIENT_EXTS):
                        continue
                    zf.write(p, arcname=item)
                    file_count += 1
                    total_bytes += p.stat().st_size
                elif p.is_dir():
                    for root, dirs, files in os.walk(p):
                        # Filter out forbidden directories
                        dirs[:] = [d for d in dirs if d not in (
                            "__pycache__", ".pytest_cache", ".git", ".venv", "tmp", "temp"
                        ) and not d.startswith("temp_") and not d.startswith("test_")]

                        for f in files:
                            lower_f = f.lower()
                            if lower_f.endswith((".pyc", ".pyo", ".zip")) or lower_f == ".ds_store":
                                continue
                            if ".attestation." in lower_f:
                                continue
                            if any(lower_f.endswith(ext) for ext in LATEX_TRANSIENT_EXTS):
                                continue

                            full_f = Path(root) / f
                            rel_name = full_f.relative_to(WORKSPACE).as_posix()
                            zf.write(full_f, arcname=rel_name)
                            file_count += 1
                            total_bytes += full_f.stat().st_size

        # Run behavioral production validation on candidate zip
        valid, msg, stats = validate_audit_archive(temp_zip_path)
        if not valid:
            raise RuntimeError(f"Candidate ZIP validation failed: {msg}")

        # Atomically move temp zip to final destination
        final_zip_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_zip_path), str(final_zip_path))

        print(f"\nAudit Bundle Successfully Created and Validated!")
        print(f"Archive:       {final_zip_path.name}")
        print(f"Destination:   {final_zip_path.resolve()}")
        print(f"Total Entries: {stats.get('total_entries')}")
        print(f"Cache Traces:  {stats.get('cache_traces')}")
        print(f"Size:          {final_zip_path.stat().st_size / (1024 * 1024):.2f} MB")
        return final_zip_path

    finally:
        if temp_zip_path.exists():
            try:
                temp_zip_path.unlink()
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=None, help="Output zip filename (default: lasr_v2_audit_bundle_v<VERSION>.zip)")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting unreleased existing target file")
    args = parser.parse_args()
    try:
        make_audit_bundle(args.out, allow_overwrite=args.overwrite)
    except Exception as exc:
        print(f"ERROR: Packaging failed: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
