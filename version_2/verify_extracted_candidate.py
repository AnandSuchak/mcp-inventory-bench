#!/usr/bin/env python3
"""Clean-room extraction verification script for candidate zip archive."""
import sys
import zipfile
import tempfile
import shutil
import subprocess
from pathlib import Path

def test_clean_extraction(zip_path: Path):
    print("=" * 80)
    print(f"CLEAN-ROOM EXTRACTION VERIFICATION: {zip_path.name}")
    print("=" * 80)
    
    temp_dir = Path(tempfile.mkdtemp(prefix="lasr_clean_verify_"))
    try:
        print(f"[*] Extracting archive to temporary directory: {temp_dir}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)
            
        print("[*] Running static formula audit in clean extraction...")
        r1 = subprocess.run([sys.executable, str(temp_dir / "version_2" / "audit_token_formulas.py")], cwd=str(temp_dir), capture_output=True, text=True)
        print(r1.stdout)
        if r1.returncode != 0:
            print(r1.stderr)
            raise RuntimeError(f"audit_token_formulas.py failed with returncode {r1.returncode}")

        print("[*] Running telemetry pilot check in clean extraction...")
        r2 = subprocess.run([sys.executable, str(temp_dir / "version_2" / "check_telemetry_pilot.py")], cwd=str(temp_dir), capture_output=True, text=True)
        print(r2.stdout)
        if r2.returncode != 0:
            print(r2.stderr)
            raise RuntimeError(f"check_telemetry_pilot.py failed with returncode {r2.returncode}")

        print("[*] Running full integrity verifier in clean extraction...")
        r3 = subprocess.run([sys.executable, str(temp_dir / "version_2" / "verify_version_2_integrity.py")], cwd=str(temp_dir), capture_output=True, text=True)
        print(r3.stdout)
        if r3.returncode != 0:
            print(r3.stderr)
            raise RuntimeError(f"verify_version_2_integrity.py failed with returncode {r3.returncode}")

        print("=" * 80)
        print("CLEAN-ROOM EXTRACTION VERIFICATION: 100% PASSED CLEANLY (ALL 3 AUDITORS EXIT 0)")
        print("=" * 80)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    zip_p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("lasr_v2_203_fresh_rerun_candidate.zip")
    test_clean_extraction(zip_p)
