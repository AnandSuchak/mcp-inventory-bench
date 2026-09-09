"""
Observational Trace Diagnostic & Empirical Signal Analyzer
Project: mcp-inventory-bench
Author: Anand S. Suchak

Answers the 6 Core Empirical Decision-Gate Questions for Dataset A:
1. First-attempt failure rate
2. Keyword distribution (pattern, enum, minimum, etc.)
3. Target path distribution (/supplier_id, /warehouse_code, etc.)
4. Retry distribution (attempts to success)
5. Schema token exposure (base vs delta, tokens-to-success)
6. Semantic consistency check (Do similar intents produce matching constraint requirements?)
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from collections import Counter, defaultdict

DEFAULT_TRACES_PATH = Path(__file__).parent.parent / "datasets" / "dataset_a" / "raw_traces.jsonl"

def analyze_traces(file_path: Path = DEFAULT_TRACES_PATH) -> Dict[str, Any]:
    if not file_path.exists():
        print(f"[!] Traces file not found: {file_path}")
        return {}

    traces = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                traces.append(json.loads(line))

    total = len(traces)
    if total == 0:
        print("[!] No traces found in file.")
        return {}

    # 1. First attempt failure count
    first_attempt_failures = 0
    for t in traces:
        attempts = t.get("attempts", [])
        if attempts and attempts[0].get("validation_status") == "FAIL":
            first_attempt_failures += 1

    first_attempt_fail_rate = (first_attempt_failures / total) * 100

    # 2 & 3. Keyword and Path distributions across all failed attempts
    keyword_counter = Counter()
    path_counter = Counter()
    attempts_counts = []
    tokens_to_success = []
    delta_tokens_list = []

    # 6. Category to constraint mappings (Semantic Signal Check)
    category_constraint_map = defaultdict(list)

    for t in traces:
        attempts = t.get("attempts", [])
        attempts_counts.append(len(attempts))
        cat = t.get("category", "Uncategorized")

        if t.get("tokens_to_success") is not None:
            tokens_to_success.append(t["tokens_to_success"])

        ledger = t.get("schema_exposure_ledger", [])
        # Base Level 1 is first item, deltas are subsequent
        deltas = [entry["tokens"] for entry in ledger[1:]]
        delta_tokens_list.append(sum(deltas))

        # Collect constraints exposed for this task
        exposed_constraints = [entry["fragment"] for entry in ledger if entry.get("reason", "").startswith("CONSTRAINT_VIOLATION")]
        if exposed_constraints:
            category_constraint_map[cat].extend(exposed_constraints)

        for a in attempts:
            for err in a.get("validation_errors", []):
                keyword_counter[err.get("keyword", "unknown")] += 1
                path_counter[err.get("path", "unknown")] += 1

    # Print clean formatted report
    print("\n" + "=" * 72)
    print(f"[*] EMPIRICAL TRACE DIAGNOSTIC REPORT ({total} Traces Evaluated)")
    print(f"[*] Dataset: {file_path}")
    print("=" * 72)

    print(f"\n[1] FIRST-ATTEMPT FAILURE RATE:")
    print(f"    - First attempts failed: {first_attempt_failures}/{total} ({first_attempt_fail_rate:.1f}%)")
    print(f"    - First attempts passed: {total - first_attempt_failures}/{total} ({100 - first_attempt_fail_rate:.1f}%)")

    print(f"\n[2] VALIDATION ERROR KEYWORDS BREAKDOWN:")
    for kw, count in keyword_counter.most_common():
        print(f"    - {kw:<15}: {count:>4} occurrences ({count/max(1, sum(keyword_counter.values()))*100:.1f}%)")

    print(f"\n[3] TARGET ERROR PATHS BREAKDOWN:")
    for path, count in path_counter.most_common():
        print(f"    - {path:<25}: {count:>4} occurrences ({count/max(1, sum(path_counter.values()))*100:.1f}%)")

    print(f"\n[4] RETRIES & ATTEMPTS DISTRIBUTION:")
    att_counter = Counter(attempts_counts)
    for att_num in sorted(att_counter.keys()):
        cnt = att_counter[att_num]
        print(f"    - {att_num} attempt(s): {cnt:>4} traces ({cnt/total*100:.1f}%)")
    avg_attempts = sum(attempts_counts) / total
    print(f"    - Mean attempts per trace: {avg_attempts:.2f}")

    print(f"\n[5] SCHEMA TOKENS EXPOSED (TTS - Tokens-to-Success):")
    if tokens_to_success:
        avg_tts = sum(tokens_to_success) / len(tokens_to_success)
        avg_delta = sum(delta_tokens_list) / max(1, len(delta_tokens_list))
        print(f"    - Average Total Tokens to Success: {avg_tts:.1f} tokens")
        print(f"    - Average Delta Tokens Added:      {avg_delta:.1f} tokens")
        print(f"    - Min / Max Tokens to Success:    {min(tokens_to_success)} / {max(tokens_to_success)} tokens")

    print(f"\n[6] SEMANTIC CONSTRAINT CONSISTENCY CHECK (Signal vs. Noise):")
    for cat, constraints in category_constraint_map.items():
        frag_counts = Counter(constraints)
        top_frag = frag_counts.most_common(2)
        top_str = ", ".join([f"{f} ({c}x)" for f, c in top_frag])
        print(f"    - Category: '{cat}'")
        print(f"      Dominant required constraints: {top_str}")

    print("\n" + "=" * 72)

    return {
        "total_traces": total,
        "first_attempt_fail_rate": first_attempt_fail_rate,
        "keyword_distribution": dict(keyword_counter),
        "path_distribution": dict(path_counter),
        "mean_attempts": round(avg_attempts, 2),
        "mean_tts": round(avg_tts, 1) if tokens_to_success else 0.0
    }

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TRACES_PATH
    analyze_traces(target)
