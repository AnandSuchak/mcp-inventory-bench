"""
Automated Git-Integration & Test Validation Gate
Project: mcp-inventory-bench
Author: Anand S. Suchak

Validates newly generated tests in staging (generated_tests/) before
automatically staging and committing them to the Git repository.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command: str) -> bool:
    """Execute shell command and print output."""
    print(f"[RUN] {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"[ERROR]\n{result.stderr}")
        return False
    if result.stdout:
        print(result.stdout.strip())
    return True

def detect_test_runner(test_file_path: str) -> str:
    """Check whether pytest or python -m unittest should be used."""
    # Check if pytest is callable
    check_pytest = subprocess.run("pytest --version", shell=True, capture_output=True)
    if check_pytest.returncode == 0:
        return f"pytest {test_file_path} -v"
    
    # Try python -m pytest
    check_py_m = subprocess.run(f"{sys.executable} -m pytest --version", shell=True, capture_output=True)
    if check_py_m.returncode == 0:
        return f"{sys.executable} -m pytest {test_file_path} -v"

    # Fallback to standard library unittest
    normalized_path = test_file_path.replace("\\", "/")
    return f"{sys.executable} -m unittest {normalized_path}"

def validate_and_commit(test_file_path: str, commit_message: str):
    """Run test validation gate, then stage and commit to Git if passed."""
    file_path = Path(test_file_path)
    if not file_path.exists():
        print(f"[!] Test file not found: {test_file_path}")
        sys.exit(1)

    print(f"\n======================================================================")
    print(f"[*] VALIDATING TEST STAGING: {file_path.name}")
    print(f"======================================================================")

    # 1. Run test validation gate
    test_cmd = detect_test_runner(str(file_path))
    print(f"[*] Executing test gate: {test_cmd}")
    if not run_command(test_cmd):
        print("\n[!] TEST VALIDATION FAILED. Aborting git commit to preserve repository integrity.")
        sys.exit(1)

    print("\n[+] All tests passed validation successfully!")

    # 2. Stage the file in Git
    print(f"[*] Staging file in Git: {test_file_path}")
    if not run_command(f"git add {test_file_path}"):
        print("[!] Failed to stage file in Git.")
        sys.exit(1)

    # 3. Commit with structured message
    print(f"[*] Committing changes: \"{commit_message}\"")
    if not run_command(f'git commit -m "{commit_message}"'):
        print("[!] Failed to commit to Git.")
        sys.exit(1)

    print("\n[SUCCESS] Test successfully validated and committed to Git!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/commit_tests.py <path_to_test_file> <commit_message>")
        sys.exit(1)

    target_path = sys.argv[1]
    msg = sys.argv[2]
    validate_and_commit(target_path, msg)
