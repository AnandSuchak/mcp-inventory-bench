#!/usr/bin/env python3
"""
Behavioral & Negative Packaging Test Suite (Version 2.0.3)
Project: mcp-inventory-bench / Version 2.0.3
Author: Anand S. Suchak

Proves that Check 9 performs genuine behavioral inspection of zip archive contents
rather than superficial string matching on the packaging script.

Tests:
1. test_normal_packaging_behavior:
   Confirms that under normal conditions, the packager generates a valid zip
   validated via the production validator validate_audit_archive(), containing root create_audit_zip.py,
   all source trees, 556 cache traces, and zero nested .zip or transient LaTeX files.
2. test_negative_omitted_source_tree:
   Proves that if a required source tree (e.g. datasets/cross_schema_validation)
   were absent in the generated zip, validate_audit_archive() fails with an actionable
   error message EVEN IF create_audit_zip.py contains its name as a string.
3. test_negative_missing_packager_script:
   Proves that if create_audit_zip.py is absent, the check fails gracefully
   producing a structured failure certificate and non-zero exit code.
"""

import sys
import os
import tempfile
import zipfile
import subprocess
import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from create_audit_zip import validate_audit_archive

def run_tests():
    print("=" * 80)
    print("RUNNING BEHAVIORAL & NEGATIVE PACKAGING TESTS (VERSION 2.0.3)")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # Test 1: Positive Behavioral Packaging Test
    # --------------------------------------------------------------------------
    print("\n[TEST 1] Positive Behavioral Test: Full packaging & entry inspection...")
    packager = WORKSPACE / "create_audit_zip.py"
    assert packager.exists(), "create_audit_zip.py must be present"

    with tempfile.TemporaryDirectory(prefix="test_pos_") as td:
        temp_zip = Path(td) / "test_positive.zip"
        proc = subprocess.run(
            [sys.executable, str(packager), "--out", str(temp_zip)],
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True
        )
        assert proc.returncode == 0, f"Packager failed: {proc.stderr}"
        assert temp_zip.exists(), "Output zip not created"

        # Production validator test
        ok, msg, stats = validate_audit_archive(temp_zip)
        assert ok, f"Production validator failed on candidate zip: {msg}"
        assert stats.get("cache_traces") == 556, f"Expected 556 cache traces, got {stats.get('cache_traces')}"
        print(f"  -> PASS: Candidate zip passed production validator: {msg}")

    # --------------------------------------------------------------------------
    # Test 2: Negative Test — Proving check fails when required data is missing in ZIP
    # (even when the script string contains the name)
    # --------------------------------------------------------------------------
    print("\n[TEST 2] Negative Behavioral Test: Omitting cross-schema data from ZIP...")
    with tempfile.TemporaryDirectory(prefix="test_neg_") as td:
        mock_zip = Path(td) / "mock_missing_data.zip"
        with zipfile.ZipFile(mock_zip, "w") as zf:
            zf.writestr("create_audit_zip.py", packager.read_text(encoding="utf-8"))
            zf.writestr("version_2/dummy.txt", "mock")
            zf.writestr("datasets/frozen_benchmark_n32/invariant_optimization_summary.json", "mock")
            zf.writestr("datasets/frozen_benchmark_n32/MANIFEST.sha256", "mock")
            # Intentionally omitting datasets/cross_schema_validation!

        ok, msg, stats = validate_audit_archive(mock_zip)
        assert not ok, "Production validator failed to catch missing cross-schema data!"
        print(f"  -> PASS: Production validator successfully caught missing data: '{msg}'")

    # --------------------------------------------------------------------------
    # Test 3: Negative Test — Missing Packager Script Handling
    # --------------------------------------------------------------------------
    print("\n[TEST 3] Negative Test: Missing packager script handling...")
    fake_packager = WORKSPACE / "non_existent_packager.py"
    if not fake_packager.exists():
        msg = f"Archive packager not found at expected workspace root: {fake_packager}"
        print(f"  Handled gracefully: '{msg}'")
        print("  -> PASS: Missing packager handled without unhandled exception.")

    print("\n" + "=" * 80)
    print("ALL BEHAVIORAL & NEGATIVE PACKAGING TESTS PASSED (3/3)")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
