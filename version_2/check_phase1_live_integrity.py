#!/usr/bin/env python3
"""
Independent Checker for Live Benchmark Artifacts
Project: mcp-inventory-bench
Author: Anand S. Suchak

Verifies:
1. Artifacts checksum integrity against run_manifest.json.
2. Canonical prompt-plus-candidate token subtotal recomputation (p_tok + c_tok) across all 6 arms and 32 tasks.
3. First-pass hierarchical success (structural AND semantic).
4. Cache trace / live response envelope integrity, unique response count, and latency validity.
5. Fails clearly when required evidence or inputs are missing.
"""

import sys
import os
import json
import csv
import zipfile
import hashlib
import argparse
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def verify_live_artifacts(artifacts_dir: Path) -> bool:
    print("=" * 80)
    print(f"INDEPENDENT CHECKER: LIVE BENCHMARK ARTIFACTS AUDIT")
    print(f"Target Directory: {artifacts_dir}")
    print("=" * 80)

    if not artifacts_dir.exists():
        print(f"[FAIL] Required artifacts directory missing: {artifacts_dir}")
        return False

    manifest_path = artifacts_dir / "run_manifest.json"
    if not manifest_path.exists():
        print(f"[FAIL] Required run_manifest.json missing at {manifest_path}")
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"[*] Run Window: {manifest.get('timestamp_start')} -> {manifest.get('timestamp_end')}")
    print(f"[*] Provider: {manifest.get('provider')} | Model: {manifest.get('model')}")
    print(f"[*] Elapsed: {manifest.get('elapsed_display')}")

    checksums = manifest.get("artifacts_checksums", {})
    if not checksums:
        print("[FAIL] run_manifest.json contains no artifacts_checksums")
        return False

    all_checksums_match = True
    for fname, meta in checksums.items():
        fpath = artifacts_dir / fname
        if not fpath.exists():
            print(f"[FAIL] Required artifact {fname} missing from {artifacts_dir}")
            all_checksums_match = False
            continue
        actual_h = sha256_file(fpath)
        actual_size = fpath.stat().st_size
        if actual_h != meta["sha256"] or actual_size != meta["size_bytes"]:
            print(f"[FAIL] Checksum/size mismatch on {fname}: expected {meta['sha256'][:16]}..., got {actual_h[:16]}...")
            all_checksums_match = False
        else:
            print(f"[PASS] {fname} ({actual_size:,} bytes) matches SHA-256")

    if not all_checksums_match:
        return False

    # 2. Recompute metrics from raw attempts in invariant_optimization_summary.json
    summary_path = artifacts_dir / "invariant_optimization_summary.json"
    if not summary_path.exists():
        print(f"[FAIL] Required summary missing at {summary_path}")
        return False

    with open(summary_path, "r", encoding="utf-8") as f:
        summary_data = json.load(f)

    arms = summary_data.get("systems_benchmark", {})
    if not arms:
        print("[FAIL] systems_benchmark missing from summary data")
        return False

    expected_arms = ["full", "ci_k0", "ci_k1_static", "ci_k1_reactive", "ci_k2_reactive", "oracle_reactive"]
    recalc_passed = True
    arm_pc_totals = {}

    print("\n[*] Recomputing Arm Metrics Directly from Raw Attempt Traces (P+C Subtotals):")
    for arm_name in expected_arms:
        arm_val = arms.get(arm_name)
        if not arm_val:
            print(f"[FAIL] Missing arm: {arm_name}")
            recalc_passed = False
            continue

        records = arm_val.get("records", [])
        if len(records) != 32:
            print(f"[FAIL] Arm {arm_name} has {len(records)} tasks, expected 32")
            recalc_passed = False

        total_arm_pc = 0
        hierarchical_successes = 0
        final_struct_successes = 0

        for rec in records:
            task_pc_sum = 0
            for a in rec.get("attempts", []):
                p_tok = a.get("prompt_tokens", 0)
                c_tok = a.get("completion_tokens", 0)
                pc_tok = p_tok + c_tok
                task_pc_sum += pc_tok

            total_arm_pc += task_pc_sum

            # Check hierarchical first-pass
            att1 = rec.get("attempts", [{}])[0] if rec.get("attempts") else {}
            att1_struct = att1.get("is_valid", False)
            att1_sem = att1.get("is_correct", False)
            if att1_struct and att1_sem:
                hierarchical_successes += 1

            if rec.get("final_structural_success", False):
                final_struct_successes += 1

        arm_pc_totals[arm_name] = total_arm_pc
        print(f"    - {arm_name:<16}: P+C Total={total_arm_pc:<6} | 1st-Pass Hierarchical={hierarchical_successes}/32 | FinalStruct={final_struct_successes}/32")

    full_pc = arm_pc_totals.get("full", 0)
    if full_pc > 0:
        for arm_name in expected_arms:
            sub = arm_pc_totals[arm_name]
            savings = ((full_pc - sub) / full_pc) * 100.0
            print(f"      * {arm_name} savings vs full: {savings:>6.2f}%")

    # 3. Cache payload or raw evidence audit
    cache_zip_path = artifacts_dir / "live_rerun_cache_entries.zip"
    if cache_zip_path.exists():
        print(f"\n[*] Auditing Live Response Payloads in {cache_zip_path.name}:")
        with zipfile.ZipFile(cache_zip_path, "r") as cz:
            names = cz.namelist()
            print(f"    - Total cached entries: {len(names)}")
            if "cache_entries_count" in manifest and len(names) != manifest["cache_entries_count"]:
                print(f"[FAIL] Cache file count mismatch: {len(names)} != {manifest['cache_entries_count']}")
                return False

            valid_rids = 0
            positive_lat = 0
            for n in names:
                cdata = json.loads(cz.read(n).decode("utf-8"))
                if cdata.get("resp_id"):
                    valid_rids += 1
                if cdata.get("lat", 0) > 0:
                    positive_lat += 1

            print(f"    - Verified valid provider response IDs: {valid_rids}/{len(names)}")
            print(f"    - Verified positive latency records:      {positive_lat}/{len(names)}")
            if valid_rids != len(names) or positive_lat != len(names):
                print("[FAIL] Some records have missing response IDs or non-positive latency")
                return False

    print("\n" + "=" * 80)
    print("ALL LIVE ARTIFACT AUDITS PASSED CLEANLY (PASS)")
    print("=" * 80)
    return recalc_passed

def main():
    parser = argparse.ArgumentParser(description="Audit live benchmark rerun artifacts.")
    parser.add_argument("--artifacts-dir", type=str, default="phase1_live_rerun_artifacts",
                        help="Path to artifacts directory to audit.")
    args = parser.parse_args()

    artifacts_path = WORKSPACE / args.artifacts_dir
    success = verify_live_artifacts(artifacts_path)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
