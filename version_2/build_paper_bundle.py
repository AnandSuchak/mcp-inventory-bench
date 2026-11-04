#!/usr/bin/env python3
"""
Idempotent Deterministic Manuscript Bundle Packager
Project: mcp-inventory-bench / Version 2.0.3
Author: Anand S. Suchak

Packages all LaTeX sources, style files, bibliography, figures, compiled PDF,
documentation, and cryptographic manifest into lasr_v2_203_manuscript_bundle.zip.

Guarantees:
1. Deterministic ZIP creation with fixed file timestamps (reproducible SHA-256).
2. Clean separation: excludes transient build artifacts (.aux, .log, .fls, etc.).
3. Generates and embeds MANIFEST.sha256 of all packaged artifacts.
4. Production archive validation via ZipFile.testzip().
5. Standalone build/review artifact (does not mutate empirical archives).
"""

import os
import sys
import hashlib
import zipfile
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent
PAPER_DIR = WORKSPACE / "version_2" / "paper_v2"
DEFAULT_OUT = WORKSPACE / "lasr_v2_203_manuscript_bundle.zip"

TRANSIENT_EXTENSIONS = {
    ".aux", ".log", ".fls", ".out", ".fdb_latexmk",
    ".bbl", ".blg", ".synctex.gz", ".toc", ".lof", ".lot"
}

REQUIRED_FILES = [
    "main_v2.tex",
    "main_v2.pdf",
    "IEEEtran.cls",
    "IEEEtran.bst",
    "references.bib",
    "README.md",
    "sections/00_abstract.tex",
    "sections/01_introduction.tex",
    "sections/02_system_architecture.tex",
    "sections/03_experimental_setup.tex",
    "sections/04_results.tex",
    "sections/05_cross_schema_results.tex",
    "sections/06_related_work.tex",
    "sections/07_discussion.tex",
    "tables/table1_systems_evaluation.tex",
    "tables/table2_paired_bootstrap.tex",
    "tables/table3_cluster_breakdown.tex",
    "tables/table4_cross_schema.tex",
    "figures/fig1_system_architecture.tex",
    "figures/fig2_systems_evaluation.pdf",
    "figures/fig3_cluster_breakdown.pdf"
]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def collect_bundle_files() -> List[Tuple[str, Path]]:
    """Collects and verifies all bundle files, rejecting transient and unapproved files."""
    if not PAPER_DIR.exists():
        raise FileNotFoundError(f"Paper directory not found: {PAPER_DIR}")

    # Verify all explicitly required files exist
    for rel in REQUIRED_FILES:
        p = PAPER_DIR / rel
        if not p.exists():
            raise FileNotFoundError(f"Missing required manuscript file: {rel}")

    items = []
    for root, dirs, files in os.walk(PAPER_DIR):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".pytest_cache", ".git")]
        for f in files:
            p = Path(root) / f
            rel = p.relative_to(PAPER_DIR).as_posix()
            
            # Skip transient files
            ext = p.suffix.lower()
            if ext in TRANSIENT_EXTENSIONS or ext == ".zip":
                continue
            if f == "MANIFEST.sha256":
                continue
            if f.startswith("."):
                continue

            items.append((rel, p))

    items.sort(key=lambda x: x[0])
    return items

def generate_manifest(bundle_files: List[Tuple[str, Path]]) -> str:
    """Generates deterministic SHA-256 manifest string for all bundled files."""
    lines = []
    for rel, p in bundle_files:
        h = sha256_file(p)
        lines.append(f"{h}  {rel}")
    lines.append("")
    return "\n".join(lines)

def build_manuscript_bundle(out_path: Path = DEFAULT_OUT) -> Tuple[Path, str, int, int]:
    """Builds a deterministic ZIP bundle containing the manuscript and returns (path, sha256, size, entry_count)."""
    bundle_files = collect_bundle_files()
    manifest_content = generate_manifest(bundle_files)
    manifest_bytes = manifest_content.encode("utf-8")

    # Write MANIFEST.sha256 to disk as well for inspection
    manifest_disk_path = PAPER_DIR / "MANIFEST.sha256"
    manifest_disk_path.write_text(manifest_content, encoding="utf-8")

    # Use fixed timestamp for deterministic reproducible ZIP archives
    fixed_time = (2026, 10, 26, 0, 0, 0)

    # Build to temp file first
    temp_zip = out_path.with_name(f"{out_path.name}.tmp")
    if temp_zip.exists():
        temp_zip.unlink()

    with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Add files in strictly sorted order
        for rel, p in bundle_files:
            data = p.read_bytes()
            zinfo = zipfile.ZipInfo(filename=rel, date_time=fixed_time)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zinfo.external_attr = 0o644 << 16
            zf.writestr(zinfo, data)

        # Add MANIFEST.sha256
        zinfo_man = zipfile.ZipInfo(filename="MANIFEST.sha256", date_time=fixed_time)
        zinfo_man.compress_type = zipfile.ZIP_DEFLATED
        zinfo_man.external_attr = 0o644 << 16
        zf.writestr(zinfo_man, manifest_bytes)

    # Validate archive
    with zipfile.ZipFile(temp_zip, "r") as zf:
        bad = zf.testzip()
        if bad is not None:
            temp_zip.unlink()
            raise RuntimeError(f"Corrupted entry in created ZIP: {bad}")
        names = zf.namelist()
        if len(names) != len(set(names)):
            temp_zip.unlink()
            raise RuntimeError("Duplicate paths detected in ZIP archive")

    # Atomically replace final destination
    if out_path.exists():
        out_path.unlink()
    temp_zip.rename(out_path)

    zip_bytes = out_path.read_bytes()
    zip_sha = sha256_bytes(zip_bytes)
    zip_size = len(zip_bytes)
    entry_count = len(names)

    return out_path, zip_sha, zip_size, entry_count

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Destination ZIP path")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = WORKSPACE / out_path

    print("Building deterministic LASR-MCP manuscript bundle...")
    path, sha, size, count = build_manuscript_bundle(out_path)
    print(f"[SUCCESS] Manuscript bundle created successfully:")
    print(f"  Archive:     {path.name}")
    print(f"  Location:    {path}")
    print(f"  SHA-256:     {sha}")
    print(f"  Size:        {size:,} bytes ({size / (1024*1024):.2f} MB)")
    print(f"  Entries:     {count} files")

if __name__ == "__main__":
    main()
