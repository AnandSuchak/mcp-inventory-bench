"""Data integrity tests for the frozen N=32 benchmark dataset."""
import json
import hashlib
from pathlib import Path

FROZEN_DIR = Path(__file__).parent.parent / "datasets" / "frozen_benchmark_n32"

def test_frozen_dataset_exists():
    summary_path = FROZEN_DIR / "invariant_optimization_summary.json"
    assert summary_path.exists(), "Frozen benchmark summary JSON does not exist"
    manifest_path = FROZEN_DIR / "MANIFEST.sha256"
    assert manifest_path.exists(), "Frozen benchmark manifest does not exist"

def test_frozen_dataset_sha256_integrity():
    summary_path = FROZEN_DIR / "invariant_optimization_summary.json"
    manifest_path = FROZEN_DIR / "MANIFEST.sha256"
    expected_hash = manifest_path.read_text(encoding="utf-8").split()[0]
    actual_hash = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    assert actual_hash == expected_hash, f"SHA-256 mismatch! Expected {expected_hash}, got {actual_hash}"

def test_frozen_dataset_schema_and_counts():
    summary_path = FROZEN_DIR / "invariant_optimization_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "systems_benchmark" in data
    bench = data["systems_benchmark"]
    expected_arms = {"full", "ci_k0", "ci_k1_static", "ci_k1_reactive", "ci_k2_reactive", "oracle_reactive"}
    assert set(bench.keys()) == expected_arms
    for arm_name in expected_arms:
        arm_data = bench[arm_name]
        assert arm_data["total_tasks"] == 32
        assert len(arm_data["records"]) == 32
