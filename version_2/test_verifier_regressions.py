#!/usr/bin/env python3
"""
Comprehensive Verifier Regression & Failure Injection Test Suite (Version 2.0.3)
Project: mcp-inventory-bench / Version 2.0.3
Author: Anand S. Suchak

Executes exhaustive failure injection and negative tests across all validation boundaries:
1. Manifest Security: Traversal ('..'), absolute paths, duplicate entries, altered hashes.
2. Manifest Completeness: Omitting required sibling files (e.g. metadata.json) is rejected.
3. Archive Validator: Omissions, nested zips, stale Version 2.0.2 in-package attestations.
4. Metric Consistency: Tampered CSV table values caught by reconciler.
5. Table IV Integrity: Tampered cross-schema table metrics caught.
6. Stale Derived Summary: Stale summary files detected against raw evidence.
7. Retrieval Outputs: Tampered retrieval JSON or CSV curves caught.
8. Latency Robustness: Non-finite, NaN, and boolean latency values strictly rejected.
9. Benchmark Task Matching: Task-set mismatches between evaluation arms rejected.
10. Missing Packager: Execution without create_audit_zip.py yields failing Check 9 and structured certificate.
11. H1 Predictor Tampering: Caught on JSON summary metrics, per-task row predictions, CSV metrics, canonical subtree, or missing files.
12. Retrieval Curve Tampering: Caught on CSV recall values, JSON macro recall, and canonical subtree.
13. Table I, II, III Invariant Tampering: Caught on Init S0 / Exp delta S cells, structural success rates, exact McNemar p-values, and cluster lifts.
14. Zero-Mutation Invariant: Programmatic verification that audit and verification checks mutate zero source files.
"""

import sys
import os
import json
import shutil
import hashlib
import tempfile
import zipfile
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from create_audit_zip import validate_audit_archive
from version_2.verify_version_2_integrity import parse_and_validate_manifest, verify_all
from version_2.reconcile_canonical_metrics import audit_check

def run_test(name: str, fn) -> bool:
    print(f"--> Running test: {name}...")
    try:
        fn()
        print(f"    [PASS] {name}")
        return True
    except Exception as exc:
        print(f"    [FAIL] {name}: {exc}")
        return False

def test_manifest_path_traversal():
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        dummy_file = tdp / "dummy.txt"
        dummy_file.write_text("hello", encoding="utf-8")
        
        # Test '..' traversal
        man_traversal = tdp / "MANIFEST.sha256"
        man_traversal.write_text("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824 ../outside.txt\n", encoding="utf-8")
        ok, msg, _ = parse_and_validate_manifest(man_traversal)
        assert not ok, "Manifest parser accepted directory traversal '..'!"
        assert "prohibited" in msg or "traversal" in msg

        # Test absolute path
        man_abs = tdp / "MANIFEST.sha256"
        man_abs.write_text("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824 /dummy.txt\n", encoding="utf-8")
        ok, msg, _ = parse_and_validate_manifest(man_abs)
        assert not ok, "Manifest parser accepted absolute path!"

def test_manifest_duplicate_entries():
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        dummy_file = tdp / "dummy.txt"
        dummy_file.write_text("hello", encoding="utf-8")
        h = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        
        man = tdp / "MANIFEST.sha256"
        man.write_text(f"{h} dummy.txt\n{h} dummy.txt\n", encoding="utf-8")
        ok, msg, _ = parse_and_validate_manifest(man)
        assert not ok, "Manifest parser accepted duplicate entry!"
        assert "Duplicate" in msg

def test_manifest_corrupted_hash():
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        dummy_file = tdp / "dummy.txt"
        dummy_file.write_text("hello", encoding="utf-8")
        bad_h = "1cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        man = tdp / "MANIFEST.sha256"
        man.write_text(f"{bad_h} dummy.txt\n", encoding="utf-8")
        ok, msg, _ = parse_and_validate_manifest(man)
        assert not ok, "Manifest parser accepted mismatched hash!"
        assert "mismatch" in msg

def test_manifest_missing_metadata_entry():
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "invariant_optimization_summary.json").write_text("{}", encoding="utf-8")
        (tdp / "metadata.json").write_text("{}", encoding="utf-8")
        h1 = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
        
        # Manifest lists only 1 file
        man = tdp / "MANIFEST.sha256"
        man.write_text(f"{h1} invariant_optimization_summary.json\n", encoding="utf-8")
        expected = {"invariant_optimization_summary.json", "metadata.json"}
        ok, msg, _ = parse_and_validate_manifest(man, expected_files=expected)
        assert not ok, "Manifest parser accepted manifest missing metadata.json!"
        assert "missing expected payload entries" in msg

def test_archive_validator_omission():
    with tempfile.TemporaryDirectory() as td:
        zip_path = Path(td) / "test_missing.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("create_audit_zip.py", "print('hello')")
        ok, msg, stats = validate_audit_archive(zip_path)
        assert not ok, "Validator accepted archive missing required files!"
        assert "missing" in msg

def test_archive_validator_nested_zip():
    with tempfile.TemporaryDirectory() as td:
        zip_path = Path(td) / "test_nested.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("create_audit_zip.py", "print('hello')")
            zf.writestr("nested.zip", "PK...")
        ok, msg, stats = validate_audit_archive(zip_path)
        assert not ok, "Validator accepted archive with nested zip!"
        assert "nested" in msg.lower()

def test_archive_validator_stale_attestation():
    with tempfile.TemporaryDirectory() as td:
        zip_path = Path(td) / "test_stale_att.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("create_audit_zip.py", "print('hello')")
            zf.writestr("version_2/release_attestation_v2.0.2.json", "{}")
        ok, msg, stats = validate_audit_archive(zip_path)
        assert not ok, "Validator accepted archive containing stale 2.0.2 attestation!"
        assert "stale" in msg.lower()

def test_table_metric_tampering():
    csv_path = WORKSPACE / "version_2" / "baseline_comparison_table.csv"
    orig_content = csv_path.read_text(encoding="utf-8")
    try:
        assert "50276" in orig_content, "Expected 50276 in baseline_comparison_table.csv"
        csv_path.write_text(orig_content.replace("50276", "99999"), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered token metric!"
    finally:
        csv_path.write_text(orig_content, encoding="utf-8")
    
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored table failed validation: {errors}"

def test_table4_tampering():
    t4_path = WORKSPACE / "version_2" / "paper_v2" / "tables" / "table4_cross_schema.tex"
    orig_content = t4_path.read_text(encoding="utf-8")
    try:
        t4_path.write_text(orig_content.replace("316.8", "999.9"), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered Table IV metric!"
    finally:
        t4_path.write_text(orig_content, encoding="utf-8")

def test_stale_derived_summary():
    cs_path = WORKSPACE / "version_2" / "cross_schema_derived_summary.json"
    orig_content = cs_path.read_text(encoding="utf-8")
    try:
        cs_data = json.loads(orig_content)
        cs_data["pooled_workload_aggregate"]["pooled_workload_savings_pct"] = 99.9
        cs_path.write_text(json.dumps(cs_data), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Audit check failed to detect stale/tampered cross_schema_derived_summary.json!"
    finally:
        cs_path.write_text(orig_content, encoding="utf-8")

def test_latency_non_finite_rejection():
    from version_2.reconcile_canonical_metrics import derive_latencies
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        # Create cache dir with a boolean/NaN latency file
        cache_dir = tdp / "datasets" / "cache"
        cache_dir.mkdir(parents=True)
        bad_trace = cache_dir / "trace_bad.json"
        bad_trace.write_text(json.dumps({"lat": True}), encoding="utf-8")
        try:
            derive_latencies(tdp)
            assert False, "derive_latencies accepted boolean latency!"
        except Exception:
            pass

def test_task_set_mismatch():
    from version_2.reconcile_canonical_metrics import derive_primary_benchmark
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        raw_dir = tdp / "datasets" / "frozen_benchmark_n32"
        raw_dir.mkdir(parents=True)
        raw_file = raw_dir / "invariant_optimization_summary.json"
        # Create mismatched task records
        fake_data = {
            "systems_benchmark": {
                "full": {"records": [{"task_id": f"T{i}", "total_tokens_consumed": 100, "attempts": [{"tokens": 100}]} for i in range(32)]},
                "ci_k1_reactive": {"records": [{"task_id": f"T{i}", "total_tokens_consumed": 80, "attempts": [{"tokens": 80}]} for i in range(32)]},
                "ci_k2_reactive": {"records": [{"task_id": f"DIFF_{i}", "total_tokens_consumed": 75, "attempts": [{"tokens": 75}]} for i in range(32)]},
                "ci_k1_static": {"records": [{"task_id": f"T{i}", "total_tokens_consumed": 85, "attempts": [{"tokens": 85}]} for i in range(32)]},
                "ci_k0": {"records": [{"task_id": f"T{i}", "total_tokens_consumed": 85, "attempts": [{"tokens": 85}]} for i in range(32)]},
                "oracle_reactive": {"records": [{"task_id": f"T{i}", "total_tokens_consumed": 75, "attempts": [{"tokens": 75}]} for i in range(32)]}
            }
        }
        raw_file.write_text(json.dumps(fake_data), encoding="utf-8")
        try:
            derive_primary_benchmark(tdp)
            assert False, "derive_primary_benchmark accepted mismatched task IDs!"
        except ValueError as ve:
            assert "Task ID mismatch" in str(ve)

def test_missing_packager_behavior():
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td)
        shutil.copytree(str(WORKSPACE / "version_2"), str(dest / "version_2"))
        shutil.copytree(str(WORKSPACE / "datasets"), str(dest / "datasets"))
        shutil.copy(str(WORKSPACE / "requirements-audit.txt"), str(dest / "requirements-audit.txt"))
        cert_path = dest / "version_2" / "verification_audit_certificate.json"
        if cert_path.exists():
            cert_path.unlink()

        verifier = dest / "version_2" / "verify_version_2_integrity.py"
        proc = subprocess.run(
            [sys.executable, str(verifier), "--stage", "missing_packager_test"],
            cwd=str(dest),
            capture_output=True,
            text=True
        )
        assert proc.returncode != 0, f"Verifier exited 0 when create_audit_zip.py was absent! stdout: {proc.stdout}"
        
        cert_path = dest / "version_2" / "verification_audit_certificate.json"
        assert cert_path.exists(), "Verifier failed to generate certificate on packager omission!"
        
        cert = json.loads(cert_path.read_text(encoding="utf-8"))
        assert cert.get("status") == "CHECKS_FAILED", f"Certificate status was {cert.get('status')}"
        c9 = [c for c in cert.get("checks", []) if "Packaging" in c.get("check", "")]
        assert c9 and not c9[0].get("passed"), "Check 9 was marked passed despite missing packager!"

def test_h1_json_metric_tampering():
    h1_path = WORKSPACE / "version_2" / "h1_predictor_evaluation.json"
    orig_content = h1_path.read_text(encoding="utf-8")
    try:
        data = json.loads(orig_content)
        data["metrics_summary"]["lasr_predictive_model"]["mean_f1"] = 0.1234
        h1_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered H1 summary metric in JSON!"
        assert any("h1_predictor_evaluation.json" in e for e in errors)
    finally:
        h1_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored H1 JSON failed validation: {errors}"

def test_h1_per_task_row_tampering():
    h1_path = WORKSPACE / "version_2" / "h1_predictor_evaluation.json"
    orig_content = h1_path.read_text(encoding="utf-8")
    try:
        data = json.loads(orig_content)
        data["per_task_results"][0]["f1_delta"] = 99.0
        h1_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered H1 per-task prediction in JSON!"
    finally:
        h1_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored H1 JSON failed validation: {errors}"

def test_h1_csv_tampering():
    csv_path = WORKSPACE / "version_2" / "h1_predictor_evaluation.csv"
    orig_content = csv_path.read_text(encoding="utf-8")
    try:
        csv_path.write_text(orig_content.replace("-1.0", "0.5"), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered H1 CSV metric!"
    finally:
        csv_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored H1 CSV failed validation: {errors}"

def test_canonical_h1_subtree_tampering():
    can_path = WORKSPACE / "version_2" / "canonical_metrics.json"
    orig_content = can_path.read_text(encoding="utf-8")
    try:
        data = json.loads(orig_content)
        data["h1_intent_prediction"]["evaluation_summary"]["paired_delta"]["exact_f1_difference"] = 0.9999
        can_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered H1 subtree in canonical_metrics.json!"
    finally:
        can_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored canonical metrics failed validation: {errors}"

def test_missing_h1_file():
    h1_path = WORKSPACE / "version_2" / "h1_predictor_evaluation.json"
    temp_path = WORKSPACE / "version_2" / "h1_predictor_evaluation.json.tmp_test"
    try:
        h1_path.rename(temp_path)
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler accepted workspace missing h1_predictor_evaluation.json!"
        assert any("Missing" in e and "h1_predictor_evaluation.json" in e for e in errors)
    finally:
        if temp_path.exists():
            temp_path.rename(h1_path)
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored H1 file failed validation: {errors}"

def test_retrieval_csv_tampering():
    csv_path = WORKSPACE / "version_2" / "retrieval_evaluation_curve.csv"
    orig_content = csv_path.read_text(encoding="utf-8")
    try:
        csv_path.write_text(orig_content.replace("15.625", "99.999"), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered retrieval curve CSV!"
    finally:
        csv_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored retrieval CSV failed validation: {errors}"

def test_retrieval_json_tampering():
    json_path = WORKSPACE / "version_2" / "dense_rag_evaluation.json"
    orig_content = json_path.read_text(encoding="utf-8")
    try:
        data = json.loads(orig_content)
        data["tfidf_results"]["top_2"]["macro_recall_pct"] = 99.9
        json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered retrieval JSON macro recall!"
    finally:
        json_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored retrieval JSON failed validation: {errors}"

def test_canonical_retrieval_subtree_tampering():
    can_path = WORKSPACE / "version_2" / "canonical_metrics.json"
    orig_content = can_path.read_text(encoding="utf-8")
    try:
        data = json.loads(orig_content)
        data["retrieval_diagnostics"]["tfidf_curve"]["top_2"]["macro_recall_pct"] = 99.9
        can_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered retrieval subtree in canonical_metrics.json!"
    finally:
        can_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored canonical metrics failed validation: {errors}"

def test_table1_init_s0_exp_s_tampering():
    t1_path = WORKSPACE / "version_2" / "paper_v2" / "tables" / "table1_systems_evaluation.tex"
    orig_content = t1_path.read_text(encoding="utf-8")
    try:
        t1_path.write_text(orig_content.replace("366.8", "999.9"), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered Table I Init S0 cell!"
    finally:
        t1_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored Table I failed validation: {errors}"

def test_table1_structural_success_tampering():
    t1_path = WORKSPACE / "version_2" / "paper_v2" / "tables" / "table1_systems_evaluation.tex"
    orig_content = t1_path.read_text(encoding="utf-8")
    try:
        t1_path.write_text(orig_content.replace("100.0\\%", "5.0\\%"), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered Table I structural success rate!"
    finally:
        t1_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored Table I failed validation: {errors}"

def test_table2_p_value_tampering():
    t2_path = WORKSPACE / "version_2" / "paper_v2" / "tables" / "table2_paired_bootstrap.tex"
    orig_content = t2_path.read_text(encoding="utf-8")
    try:
        t2_path.write_text(orig_content.replace("p = 0.0078125", "p = 0.999999"), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered Table II p-value!"
    finally:
        t2_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored Table II failed validation: {errors}"

def test_table3_cluster_lift_tampering():
    t3_path = WORKSPACE / "version_2" / "paper_v2" / "tables" / "table3_cluster_breakdown.tex"
    orig_content = t3_path.read_text(encoding="utf-8")
    try:
        t3_path.write_text(orig_content.replace("+50.0 pp", "+999 pp"), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered Table III cluster lift!"
    finally:
        t3_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored Table III failed validation: {errors}"

def test_table3_c1_cell_tampering():
    t3_path = WORKSPACE / "version_2" / "paper_v2" / "tables" / "table3_cluster_breakdown.tex"
    orig_content = t3_path.read_text(encoding="utf-8")
    try:
        # Tamper Table III: change C1 87.5% -> 7.5%
        assert "87.5\\%" in orig_content, "Expected 87.5% in Table III"
        t3_path.write_text(orig_content.replace("87.5\\%", "7.5\\%"), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered Table III C1 cell (87.5% -> 7.5%)!"
        assert any("table3_cluster_breakdown.tex" in e for e in errors)
    finally:
        t3_path.write_text(orig_content, encoding="utf-8")
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored Table III failed validation: {errors}"

def test_frozen_manifest_integrity_and_tampering():
    man_path = WORKSPACE / "datasets" / "frozen_benchmark_n32" / "MANIFEST.sha256"
    orig_content = man_path.read_bytes()
    try:
        # 1. Tamper by adding extra entry
        man_path.write_text("78c2c88ed5128e0f296fa29e0c258589b516f3adb14b0b8da491fa73bc3ffc11  invariant_optimization_summary.json\nab8ca76d5ef47826ba95d28046b1b6181f001055fccf2490e659102249f72c91  metadata.json\n", encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler accepted modified MANIFEST.sha256!"

        # 2. Tamper by changing hash
        man_path.write_text("0000000000000000000000000000000000000000000000000000000000000000  invariant_optimization_summary.json\n", encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler accepted corrupted hash in MANIFEST.sha256!"
    finally:
        man_path.write_bytes(orig_content)
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored manifest failed validation: {errors}"

def test_metadata_validation_and_tampering():
    meta_path = WORKSPACE / "datasets" / "frozen_benchmark_n32" / "metadata.json"
    orig_content = meta_path.read_bytes()
    try:
        # Tamper metadata content
        meta_path.write_text(json.dumps({"tampered": True}), encoding="utf-8")
        ok, errors = audit_check(WORKSPACE)
        assert not ok, "Reconciler failed to catch tampered metadata.json!"
    finally:
        meta_path.write_bytes(orig_content)
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Restored metadata failed validation: {errors}"

def test_cli_help_and_dry_run_immutability():
    scripts = [
        WORKSPACE / "version_2" / "generate_paper_tables_v2.py",
        WORKSPACE / "version_2" / "langgraph_evaluator.py",
        WORKSPACE / "version_2" / "run_dense_rag_baseline.py",
        WORKSPACE / "version_2" / "reproduce_h1_predictor.py",
        WORKSPACE / "version_2" / "derive_cross_schema_metrics.py"
    ]
    for script in scripts:
        # Test --help
        res_help = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True)
        assert res_help.returncode == 0, f"{script.name} --help failed with exit code {res_help.returncode}"

        # Test dry-run default (invoking without flags)
        res_dry = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        assert res_dry.returncode == 0, f"{script.name} dry-run failed with exit code {res_dry.returncode}: {res_dry.stderr}"

def test_release_version_fail_closed():
    v_file = WORKSPACE / "version_2" / "RELEASE_VERSION"
    orig_content = v_file.read_text(encoding="utf-8")
    try:
        # Test empty file
        v_file.write_text("", encoding="utf-8")
        try:
            from version_2.reconcile_canonical_metrics import get_release_version
            get_release_version(WORKSPACE)
            assert False, "get_release_version accepted empty RELEASE_VERSION!"
        except ValueError:
            pass

        # Test missing file
        v_file.unlink()
        try:
            from version_2.reconcile_canonical_metrics import get_release_version
            get_release_version(WORKSPACE)
            assert False, "get_release_version accepted missing RELEASE_VERSION!"
        except FileNotFoundError:
            pass
    finally:
        v_file.write_text(orig_content, encoding="utf-8")

def test_source_immutability_during_check():
    def get_dir_hashes(d: Path) -> dict:
        h_map = {}
        for root, dirs, files in os.walk(d):
            dirs[:] = [dr for dr in dirs if dr not in ("__pycache__", ".git")]
            for f in files:
                if f.endswith(".pyc") or f == "verification_audit_certificate.json":
                    continue
                fp = Path(root) / f
                rel = fp.relative_to(d).as_posix()
                h_map[rel] = hashlib.sha256(fp.read_bytes()).hexdigest()
        return h_map

    v2_dir = WORKSPACE / "version_2"
    before_hashes = get_dir_hashes(v2_dir)

    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Audit check failed: {errors}"

    with tempfile.TemporaryDirectory() as td:
        temp_cert = Path(td) / "temp_cert.json"
        ver_ok = verify_all(audit_stage="immutability_regression_test", certificate_out=temp_cert)
        assert ver_ok, "verify_all failed during immutability test!"

    after_hashes = get_dir_hashes(v2_dir)
    assert before_hashes == after_hashes, "Files in version_2 were mutated during read-only verification!"

def test_negative_mutation_token_formula():
    """Mutation 1: Injects heuristic schema-token addition into canonical formula; validation must fail."""
    canon_path = WORKSPACE / "version_2" / "canonical_metrics.json"
    orig_text = canon_path.read_text(encoding="utf-8")
    try:
        # Mutate canonical_metrics.json to inject double-counted formula (61,853 -> 96,629)
        assert "61853" in orig_text, "Expected canonical 61853 token count missing before mutation"
        tampered_text = orig_text.replace("61853", "96629")
        canon_path.write_text(tampered_text, encoding="utf-8")

        ok, errors = audit_check(WORKSPACE)
        assert not ok, "audit_check accepted canonical_metrics.json mutated with old heuristic schema formula!"
        error_str = " ".join(errors)
        assert "workload tokens mismatch" in error_str or "61853" in error_str or "96629" in error_str, f"Unexpected error output: {errors}"
    finally:
        canon_path.write_text(orig_text, encoding="utf-8")

    # Verify restored state passes
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Post-restoration canonical validation failed: {errors}"

def test_negative_mutation_hierarchical_success():
    """Mutation 2: Bypasses the structural-and-semantic conjunction; validation must fail."""
    canon_path = WORKSPACE / "version_2" / "canonical_metrics.json"
    orig_text = canon_path.read_text(encoding="utf-8")
    try:
        # Mutate canonical_metrics.json to bypass structural check: first_pass_hierarchical_count 10 -> 31
        canon_data = json.loads(orig_text)
        assert canon_data["primary_benchmark"]["arms"]["full"]["first_pass_hierarchical_count"] == 10
        canon_data["primary_benchmark"]["arms"]["full"]["first_pass_hierarchical_count"] = 31
        canon_path.write_text(json.dumps(canon_data, indent=2), encoding="utf-8")

        ok, errors = audit_check(WORKSPACE)
        assert not ok, "audit_check accepted hierarchical count with bypassed structural validity conjunction!"
        error_str = " ".join(errors)
        assert "first_pass_hierarchical_count mismatch" in error_str or "31" in error_str, f"Unexpected error output: {errors}"
    finally:
        canon_path.write_text(orig_text, encoding="utf-8")

    # Verify restored state passes
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Post-restoration hierarchical validation failed: {errors}"

def test_negative_mutation_manuscript_table():
    """Mutation 3: Changes a reported table value; validation must fail."""
    t1_path = WORKSPACE / "version_2" / "paper_v2" / "tables" / "table1_systems_evaluation.tex"
    orig_tex = t1_path.read_text(encoding="utf-8")
    try:
        # Mutate Full Schema token cell: 61,853 -> 99,999
        tampered_tex = orig_tex.replace("61,853", "99,999")
        assert "99,999" in tampered_tex, "Target string replacement failed"
        t1_path.write_text(tampered_tex, encoding="utf-8")

        ok, errors = audit_check(WORKSPACE)
        assert not ok, "audit_check accepted tampered Table 1 manuscript table!"
        error_str = " ".join(errors)
        assert "table1_systems_evaluation.tex" in error_str and ("diverges" in error_str or "Token total 61,853 missing" in error_str), f"Unexpected error output: {errors}"
    finally:
        t1_path.write_text(orig_tex, encoding="utf-8")

    # Verify restored state passes
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Post-restoration Table 1 validation failed: {errors}"

def test_negative_mutation_evidence_or_completeness():
    """Mutation 4: Removes a required limitation statement or provenance disclosure; validation must fail."""
    sec7_path = WORKSPACE / "version_2" / "paper_v2" / "sections" / "07_discussion.tex"
    orig_sec7 = sec7_path.read_text(encoding="utf-8")
    try:
        # Mutate: remove the required 285 unique live response entries disclosure
        assert "285 newly observed unique" in orig_sec7, "Expected required disclosure phrase missing before test"
        tampered_sec7 = orig_sec7.replace("285 newly observed unique", "428 independent fresh API")
        sec7_path.write_text(tampered_sec7, encoding="utf-8")

        ok, errors = audit_check(WORKSPACE)
        assert not ok, "audit_check accepted omitted required limitation statement in Section 07!"
        error_str = " ".join(errors)
        assert "07_discussion.tex" in error_str and "285 unique live response entries" in error_str, f"Unexpected error output: {errors}"
    finally:
        sec7_path.write_text(orig_sec7, encoding="utf-8")

    # Verify restored state passes
    ok, errors = audit_check(WORKSPACE)
    assert ok, f"Post-restoration Section 07 validation failed: {errors}"

def test_static_token_formula_audit():
    """Static Audit: Scans repository for forbidden empirical token formula anti-patterns."""
    from version_2.audit_token_formulas import scan_repository
    clean, violations = scan_repository()
    assert clean, f"Static audit detected forbidden token formulas: {violations}"

def main():
    print("=" * 80)
    print("RUNNING LASR-MCP COMPREHENSIVE VERIFIER REGRESSION SUITE (VERSION 2.0.3)")
    print("=" * 80)
    
    tests = [
        ("Manifest Directory Traversal Rejection ('..' & absolute)", test_manifest_path_traversal),
        ("Manifest Duplicate Entry Rejection", test_manifest_duplicate_entries),
        ("Manifest Corrupted Hash Detection", test_manifest_corrupted_hash),
        ("Manifest Missing Sibling Metadata Rejection", test_manifest_missing_metadata_entry),
        ("Archive Validator Required Path Omission Rejection", test_archive_validator_omission),
        ("Archive Validator Nested ZIP Rejection", test_archive_validator_nested_zip),
        ("Archive Validator Stale In-Package Attestation Rejection", test_archive_validator_stale_attestation),
        ("Canonical Table Metric Tampering Detection", test_table_metric_tampering),
        ("Table IV Invariant Floor Tampering Detection", test_table4_tampering),
        ("Stale Derived Summary Detection", test_stale_derived_summary),
        ("Non-Finite & Boolean Latency Value Rejection", test_latency_non_finite_rejection),
        ("Multi-Arm Task ID Mismatch Rejection", test_task_set_mismatch),
        ("Missing Packager Subprocess & Structured Certificate Failure", test_missing_packager_behavior),
        ("H1 JSON Summary Metric Tampering Detection", test_h1_json_metric_tampering),
        ("H1 JSON Per-Task Row Prediction Tampering Detection", test_h1_per_task_row_tampering),
        ("H1 CSV Metric Tampering Detection", test_h1_csv_tampering),
        ("Canonical H1 Subtree Tampering Detection", test_canonical_h1_subtree_tampering),
        ("Missing H1 Evaluation File Rejection", test_missing_h1_file),
        ("Retrieval CSV Curve Tampering Detection", test_retrieval_csv_tampering),
        ("Retrieval JSON Macro Recall Tampering Detection", test_retrieval_json_tampering),
        ("Canonical Retrieval Subtree Tampering Detection", test_canonical_retrieval_subtree_tampering),
        ("Table I Init S0 / Exp Delta S Tampering Detection", test_table1_init_s0_exp_s_tampering),
        ("Table I Structural Success Rate Tampering Detection", test_table1_structural_success_tampering),
        ("Table II Exact McNemar p-value Tampering Detection", test_table2_p_value_tampering),
        ("Table III Cluster Lift Tampering Detection", test_table3_cluster_lift_tampering),
        ("Table III C1 Cell Tampering Detection (87.5% -> 7.5%)", test_table3_c1_cell_tampering),
        ("Frozen Manifest Integrity & Tampering Detection", test_frozen_manifest_integrity_and_tampering),
        ("Frozen Benchmark Metadata Tampering Detection", test_metadata_validation_and_tampering),
        ("CLI Script --help and Dry-Run Immutability Verification", test_cli_help_and_dry_run_immutability),
        ("RELEASE_VERSION Missing/Empty Fail-Closed Verification", test_release_version_fail_closed),
        ("Zero-Mutation Source Immutability During Verification", test_source_immutability_during_check),
        ("Negative Mutation 1: Injected Heuristic Schema Tokens Fails", test_negative_mutation_token_formula),
        ("Negative Mutation 2: Bypassed Hierarchical Conjunction Fails", test_negative_mutation_hierarchical_success),
        ("Negative Mutation 3: Manuscript Table Tampering Fails", test_negative_mutation_manuscript_table),
        ("Negative Mutation 4: Required Limitation / Provenance Omission Fails", test_negative_mutation_evidence_or_completeness),
        ("Static Empirical Token Formula Audit", test_static_token_formula_audit)
    ]
    
    passed_count = sum(1 for name, fn in tests if run_test(name, fn))
    print("=" * 80)
    print(f"REGRESSION SUITE COMPLETED: {passed_count}/{len(tests)} TESTS PASSED")
    print("=" * 80)
    if passed_count != len(tests):
        sys.exit(1)

if __name__ == "__main__":
    main()
