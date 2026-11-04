#!/usr/bin/env python3
"""
Static Token Formula Auditor
Project: mcp-inventory-bench
Author: Anand S. Suchak

Scans the repository for forbidden empirical token formula anti-patterns:
1. p_tok + curr_schema_tokens + c_tok
2. p_tok + estimate_tokens(exposed_schema) + c_tok
3. base_prompt_tokens + total_schema_tokens + completion_tokens
4. prompt_tokens + schema_tokens + completion_tokens
5. Adding schema token estimates to provider prompt tokens in active empirical runners.

Narrowly documented exceptions:
- Deterministic simulation harness: trace/cross_schema_benchmark.py (synthetic simulation model)
- Archival / test regression fixtures: test_verifier_regressions.py (explicit negative test injections)
"""

import sys
import os
import re
from pathlib import Path
from typing import List, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent

FORBIDDEN_PATTERNS = [
    (r"p_tok\s*\+\s*curr_schema_tokens\s*\+\s*c_tok", "Double-counts schema tokens (p_tok + curr_schema_tokens + c_tok)"),
    (r"p_tok\s*\+\s*estimate_tokens\s*\(\s*exposed_schema\s*\)\s*\+\s*c_tok", "Double-counts schema tokens (p_tok + estimate_tokens(exposed_schema) + c_tok)"),
    (r"base_prompt_tokens\s*\+\s*total_schema_tokens\s*\+\s*completion_tokens", "Double-counts schema tokens into prompt tokens"),
    (r"prompt_tokens\s*\+\s*schema_tokens\s*\+\s*completion_tokens", "Double-counts schema tokens into Phase 1 recomputation"),
]

ALLOWED_EXCEPTIONS = {
    "trace/cross_schema_benchmark.py": "Documented deterministic cross-schema synthetic simulation logic",
    "version_2/test_verifier_regressions.py": "Isolated negative mutation test fixtures testing validator fail-closed boundary",
    "version_2/audit_token_formulas.py": "The auditor itself defining forbidden pattern specifications",
}

def scan_repository() -> Tuple[bool, List[str]]:
    violations = []

    for root, dirs, files in os.walk(WORKSPACE):
        # Skip git, caches, virtual environments, and temporary directories
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "venv", ".venv", "tmp", "scratch")]
        for f in files:
            if not f.endswith(".py"):
                continue
            fpath = Path(root) / f
            rel_path = fpath.relative_to(WORKSPACE).as_posix()

            if rel_path in ALLOWED_EXCEPTIONS:
                continue

            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                continue

            for pattern, desc in FORBIDDEN_PATTERNS:
                matches = list(re.finditer(pattern, content))
                if matches:
                    for m in matches:
                        line_no = content[:m.start()].count("\n") + 1
                        violations.append(f"{rel_path}:{line_no}: FORBIDDEN PATTERN: {desc}")

    return len(violations) == 0, violations

def main():
    print("=" * 80)
    print("STATIC AUDIT: EMPIRICAL TOKEN FORMULA INTEGRITY")
    print("=" * 80)
    clean, violations = scan_repository()
    if clean:
        print("[PASS] Zero forbidden double-counting token formulas detected across repository.")
        print(f"       Permitted simulation/test exceptions: {list(ALLOWED_EXCEPTIONS.keys())}")
        print("=" * 80)
        sys.exit(0)
    else:
        print(f"[FAIL] Detected {len(violations)} forbidden token formula violations:")
        for v in violations:
            print(f"  - {v}")
        print("=" * 80)
        sys.exit(1)

if __name__ == "__main__":
    main()
