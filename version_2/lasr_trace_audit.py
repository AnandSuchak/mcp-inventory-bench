#!/usr/bin/env python3
"""Audit LASR-MCP traces without inventing missing measurements.

Standard-library-only utility for the mcp-inventory-bench repository.

What it can compute:
  * API/model-call counts when calls are explicitly represented in trace records.
  * p50/p99 for locally recorded latency fields (it will NOT synthesize AST latency).
  * an offline lexical TF-IDF cosine-retrieval recall@k, if task records contain
    a query plus ground-truth constraint IDs and --schema-json points to the
    full JSON Schema. This is a transparent local baseline, NOT Google's
    text-embedding-004 dense embedding baseline.

No API calls are made. Missing or ambiguous fields are reported as TBD.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

DATA_EXTS = {".json", ".jsonl", ".ndjson", ".csv", ".tsv"}
IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}

QUERY_KEYS = ("query", "user_query", "prompt", "task_prompt", "instruction", "user_intent", "question")
TRUTH_KEYS = ("ground_truth_constraints", "target_constraints", "required_constraints", "constraint_ids", "gold_constraints", "expected_constraints", "target_constraint_ids")
ARM_KEYS = ("system_arm", "arm", "variant", "configuration", "config", "method", "baseline", "system", "strategy")
LATENCY_KEYS = (
    "ast_splice_ms", "splice_ms", "recompose_ms", "recomposition_ms",
    "local_recomposition_ms", "local_ast_splice_ms", "pointer_lookup_ms", "tree_merge_ms",
    "ast_splice_us", "splice_us", "recompose_us", "recomposition_us",
    "local_recomposition_us", "local_ast_splice_us", "pointer_lookup_us", "tree_merge_us",
    "ast_splice_ns", "splice_ns", "recompose_ns", "recomposition_ns",
    "local_recomposition_ns", "local_ast_splice_ns", "pointer_lookup_ns", "tree_merge_ns",
    "ast_splice_s", "splice_s", "recompose_s", "recomposition_s",
    "local_recomposition_s", "local_ast_splice_s", "pointer_lookup_s", "tree_merge_s",
)
CALL_COUNT_KEYS = ("api_call_count", "model_call_count", "llm_call_count", "request_count", "num_api_calls", "num_model_calls", "api_calls", "model_calls", "llm_calls", "requests", "model_request_events", "api_call_records")
EVENT_KEYS = ("event_type", "event", "kind", "operation", "type", "name", "request_type")


def norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def walk_records(obj: Any, source: str, inherited: dict[str, Any] | None = None, in_call_collection: bool = False) -> Iterable[dict[str, Any]]:
    """Yield dictionaries recursively, preserving source, arm, and call-list context."""
    inherited = inherited or {}
    if isinstance(obj, dict):
        rec = dict(obj)
        for key, value in inherited.items():
            rec.setdefault(key, value)
        rec.setdefault("__source_file__", source)
        if in_call_collection:
            rec["__inside_call_collection__"] = True
        yield rec
        context = dict(inherited)
        for key, value in rec.items():
            if norm_key(key) in {norm_key(x) for x in ARM_KEYS} | {"task_id", "task", "task_name", "case_id", "benchmark_case"} and isinstance(value, (str, int, float)):
                context.setdefault(key, value)
        call_collection_keys = {norm_key(x) for x in CALL_COUNT_KEYS}
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                is_call_list = isinstance(value, list) and norm_key(key) in call_collection_keys
                yield from walk_records(value, source, context, in_call_collection or is_call_list)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_records(value, source, inherited, in_call_collection)


def read_file(path: Path) -> list[dict[str, Any]]:
    try:
        if path.suffix.lower() in {".jsonl", ".ndjson"}:
            items = []
            with path.open("r", encoding="utf-8-sig") as f:
                for line_no, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line)
                        items.extend(walk_records(value, f"{path}:{line_no}"))
                    except json.JSONDecodeError:
                        continue
            return items
        if path.suffix.lower() in {".csv", ".tsv"}:
            delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
            with path.open("r", encoding="utf-8-sig", newline="") as f:
                return [dict(row, __source_file__=str(path)) for row in csv.DictReader(f, delimiter=delimiter)]
        if path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8-sig") as f:
                return list(walk_records(json.load(f), str(path)))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, csv.Error):
        return []
    return []


def find_key(record: dict[str, Any], aliases: Iterable[str]) -> tuple[str | None, Any]:
    wanted = {norm_key(a) for a in aliases}
    for key, val in record.items():
        if norm_key(key) in wanted and val not in (None, ""):
            return key, val
    return None, None


def get_arm(record: dict[str, Any]) -> str:
    _, value = find_key(record, ARM_KEYS)
    if isinstance(value, (str, int, float)):
        return str(value)
    return "UNKNOWN_ARM"


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", value.replace(",", ""))
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                pass
    return None


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0]
    # Linear interpolation between adjacent order statistics.
    pos = (len(vals) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)


def flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join(f"{k} {flatten_text(v)}" for k, v in value.items())
    return ""


def is_audit_report(path: Path) -> bool:
    """Identify this utility's JSON output so it cannot be re-ingested as raw data."""
    if path.suffix.lower() != ".json":
        return False
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            obj = json.load(f)
        return isinstance(obj, dict) and {
            "api_calls_and_recorded_latency", "offline_cosine_rag", "local_ast_latency_note"
        }.issubset(obj.keys())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False


def collect_files(root: Path, out_path: Path | None = None, exclude_patterns: list[str] | None = None) -> list[Path]:
    result: list[Path] = []
    out_resolved = out_path.resolve() if out_path is not None else None
    exclude_patterns = exclude_patterns or []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in DATA_EXTS:
            continue
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        # Exclude the requested output path and this tool's reports by structure,
        # regardless of filename (e.g. report.json), to avoid circular aggregation.
        if out_resolved is not None and p.resolve() == out_resolved:
            continue
        if is_audit_report(p):
            continue
        rel = p.relative_to(root).as_posix()
        if p.name.startswith("lasr_trace_audit"):
            continue
        if any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(p.name, pat) for pat in exclude_patterns):
            continue
        result.append(p)
    return sorted(result)


def parse_pointer(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        return []
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def json_pointer(parts: list[str]) -> str:
    return "" if not parts else "/" + "/".join(p.replace("~", "~0").replace("/", "~1") for p in parts)


def schema_chunks(schema: Any, prefix: list[str] | None = None) -> list[dict[str, str]]:
    """Make a constraint catalog from JSON Schema keyword nodes.

    IDs use the schema-location pointer, e.g. /properties/warehouse_code/enum.
    This is a lexical catalog for a reproducible offline baseline, not embeddings.
    """
    prefix = prefix or []
    chunks: list[dict[str, str]] = []
    if not isinstance(schema, dict):
        return chunks
    keywords = {
        "type", "enum", "const", "pattern", "format", "required", "minimum", "maximum",
        "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength",
        "minItems", "maxItems", "uniqueItems", "minProperties", "maxProperties",
        "additionalProperties", "propertyNames", "dependentRequired", "dependentSchemas",
        "oneOf", "anyOf", "allOf", "not", "contains", "prefixItems"
    }
    # A chunk is created per constraint keyword, including nested values as text.
    for key, val in schema.items():
        if key in keywords:
            path = prefix + [key]
            chunks.append({"id": json_pointer(path), "text": f"{json_pointer(prefix)} {key} {flatten_text(val)}"})
    # Walk schema-bearing children; don't recursively treat enum or examples as schemas.
    schema_children = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}
    for key, val in schema.items():
        if key in schema_children and isinstance(val, dict):
            for name, child in val.items():
                chunks.extend(schema_chunks(child, prefix + [key, name]))
        elif key in {"items", "additionalProperties", "contains", "not", "if", "then", "else"} and isinstance(val, dict):
            chunks.extend(schema_chunks(val, prefix + [key]))
        elif key in {"allOf", "anyOf", "oneOf", "prefixItems"} and isinstance(val, list):
            for i, child in enumerate(val):
                chunks.extend(schema_chunks(child, prefix + [key, str(i)]))
    return chunks


def tokenize(text: str) -> list[str]:
    # Split schema identifiers such as warehouse_code and WH-US-EAST into
    # their component terms so user language can match property/value chunks.
    raw = re.findall(r"[a-zA-Z_][a-zA-Z0-9_/-]*|\d+", text)
    tokens: list[str] = []
    for item in raw:
        tokens.extend(part.lower() for part in re.split(r"[_/-]+", item) if part)
    return tokens


def tfidf_vectors(documents: list[str]) -> list[dict[str, float]]:
    tokenized = [tokenize(d) for d in documents]
    df: Counter[str] = Counter()
    for tokens in tokenized:
        df.update(set(tokens))
    n = max(1, len(documents))
    vectors = []
    for tokens in tokenized:
        counts = Counter(tokens)
        vec = {term: (1 + math.log(count)) * (math.log((1 + n) / (1 + df[term])) + 1) for term, count in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values()))
        vectors.append({k: v / norm for k, v in vec.items()} if norm else {})
    return vectors


def cosine_sparse(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def ids_from(value: Any) -> set[str]:
    if isinstance(value, str):
        # Preserve pointer-like IDs and split simple delimited label strings.
        if value.startswith("/"):
            return {value}
        return {v.strip() for v in re.split(r"[,;\n]", value) if v.strip()}
    if isinstance(value, list):
        out: set[str] = set()
        for item in value:
            out |= ids_from(item)
        return out
    if isinstance(value, dict):
        for k in ("id", "path", "schema_path", "pointer", "constraint_id", "label"):
            if k in value:
                return ids_from(value[k])
    return set()


def extract_rag_tasks(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for rec in records:
        _, query = find_key(rec, QUERY_KEYS)
        _, truth = find_key(rec, TRUTH_KEYS)
        q = flatten_text(query).strip()
        target_ids = ids_from(truth)
        if q and target_ids:
            key = (q, tuple(sorted(target_ids)))
            if key not in seen:
                tasks.append({"query": q, "truth": target_ids, "arm": get_arm(rec), "source": rec.get("__source_file__", "")})
                seen.add(key)
    return tasks


def analyze(root: Path, schema_file: Path | None, top_k: int, out_path: Path | None = None, exclude_patterns: list[str] | None = None) -> dict[str, Any]:
    files = collect_files(root, out_path=out_path, exclude_patterns=exclude_patterns)
    records: list[dict[str, Any]] = []
    for file in files:
        records.extend(read_file(file))

    # Count calls only from explicit call-count fields or identifiable request events.
    calls_by_arm: Counter[str] = Counter()
    call_evidence: Counter[str] = Counter()
    latency_by_arm: dict[str, list[float]] = defaultdict(list)
    latency_fields_seen: Counter[str] = Counter()
    event_rows_by_arm: Counter[str] = Counter()

    request_terms = ("model_request", "llm_request", "api_request", "generate_content", "generatecontent", "inference_request", "chat_completion", "model_call", "llm_call")
    for rec in records:
        arm = get_arm(rec)
        explicit_count = False
        for key, value in rec.items():
            nk = norm_key(key)
            if nk in {norm_key(k) for k in CALL_COUNT_KEYS}:
                if isinstance(value, list):
                    calls_by_arm[arm] += len(value)
                    call_evidence[arm] += 1
                    explicit_count = True
                else:
                    val = number(value)
                    if val is not None and val >= 0 and val.is_integer():
                        calls_by_arm[arm] += int(val)
                        call_evidence[arm] += 1
                        explicit_count = True
                if explicit_count:
                    break
        if not explicit_count:
            event_parts = [str(rec[k]).lower() for k in rec if norm_key(k) in {norm_key(x) for x in EVENT_KEYS} and rec[k] is not None]
            event = " ".join(event_parts)
            # Count only explicit request-like events, not arbitrary log rows.
            if not rec.get("__inside_call_collection__") and any(term in event for term in request_terms):
                calls_by_arm[arm] += 1
                call_evidence[arm] += 1
                event_rows_by_arm[arm] += 1
        for key, value in rec.items():
            nk = norm_key(key)
            if nk in {norm_key(k) for k in LATENCY_KEYS}:
                val = number(value)
                if val is not None and val >= 0:
                    # Unit is inferred only from the field suffix; bare/unknown fields
                    # are not converted or guessed.
                    if nk.endswith("_ns") or "nanosecond" in nk:
                        val /= 1_000_000
                    elif nk.endswith("_us") or "microsecond" in nk:
                        val /= 1_000
                    elif (nk.endswith("_s") and not nk.endswith("_ms")) or "seconds" in nk or "_seconds_" in nk:
                        val *= 1_000
                    latency_by_arm[arm].append(val)
                    latency_fields_seen[nk] += 1

    arms = sorted(set(calls_by_arm) | set(latency_by_arm))
    call_report = []
    for arm in arms:
        call_report.append({
            "arm": arm,
            "api_calls_counted": calls_by_arm[arm] if call_evidence[arm] else None,
            "records_supporting_call_count": call_evidence[arm],
            "explicit_request_event_rows": event_rows_by_arm[arm],
            "local_latency_samples": len(latency_by_arm[arm]),
            "local_latency_p50_ms": round(percentile(latency_by_arm[arm], 0.50), 6) if latency_by_arm[arm] else None,
            "local_latency_p99_ms": round(percentile(latency_by_arm[arm], 0.99), 6) if latency_by_arm[arm] else None,
        })

    rag_report: dict[str, Any] = {"status": "TBD", "reason": "Need --schema-json and task records with query + ground-truth constraint IDs."}
    rag_tasks = extract_rag_tasks(records)
    if schema_file and schema_file.is_file() and rag_tasks:
        try:
            schema = json.loads(schema_file.read_text(encoding="utf-8"))
            chunks = schema_chunks(schema)
            if not chunks:
                rag_report = {"status": "TBD", "reason": "Schema parsed but no supported constraint-keyword chunks were found."}
            else:
                corpus = [c["text"] for c in chunks] + [t["query"] for t in rag_tasks]
                vectors = tfidf_vectors(corpus)
                chunk_vectors = vectors[:len(chunks)]
                query_vectors = vectors[len(chunks):]
                hits, total_gold, task_details = 0, 0, []
                recalls = []
                for task, qvec in zip(rag_tasks, query_vectors):
                    ranked_idx = sorted(range(len(chunks)), key=lambda i: cosine_sparse(qvec, chunk_vectors[i]), reverse=True)[:top_k]
                    retrieved = {chunks[i]["id"] for i in ranked_idx}
                    gold = task["truth"]
                    found = gold & retrieved
                    denom = len(gold)
                    recall = len(found) / denom if denom else 0.0
                    recalls.append(recall)
                    hits += len(found)
                    total_gold += denom
                    task_details.append({"query": task["query"], "ground_truth_ids": sorted(gold), "retrieved_ids": [chunks[i]["id"] for i in ranked_idx], "gold_recalled": sorted(found), "recall_at_k": round(recall, 6)})
                rag_report = {
                    "status": "computed",
                    "method": "local TF-IDF weighted lexical vectors + cosine similarity (not text-embedding-004)",
                    "tasks_evaluated": len(rag_tasks),
                    "schema_constraint_chunks": len(chunks),
                    "k": top_k,
                    "micro_recall_at_k": round(hits / total_gold, 6) if total_gold else None,
                    "macro_recall_at_k": round(statistics.mean(recalls), 6) if recalls else None,
                    "per_task": task_details,
                    "warning": "This is a reproducible lexical-cosine baseline. Do not describe it as dense embedding Tool-RAG or substitute its result for an embedding-model experiment."
                }
        except (OSError, json.JSONDecodeError) as exc:
            rag_report = {"status": "TBD", "reason": f"Could not read schema JSON: {exc}"}
    elif schema_file and not schema_file.is_file():
        rag_report = {"status": "TBD", "reason": f"Schema file does not exist: {schema_file}"}
    elif schema_file and not rag_tasks:
        rag_report = {"status": "TBD", "reason": "No task records contain a recognized query field and ground-truth constraint IDs. Inspect the data format and add the relevant aliases if needed."}

    return {
        "root": str(root.resolve()),
        "data_files_read": len(files),
        "records_parsed": len(records),
        "data_files": [str(p.relative_to(root)) for p in files],
        "excluded_patterns": exclude_patterns or [],
        "api_calls_and_recorded_latency": call_report,
        "local_latency_fields_seen": dict(latency_fields_seen),
        "local_ast_latency_note": (
            "Latency is summarized only if existing trace fields record a recomposition/splice duration. "
            "If no samples are listed, instrument the actual LASR recomposition function and rerun; "
            "a synthetic JSON operation would not measure LASR's implementation."
        ),
        "offline_cosine_rag": rag_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root to scan (default: current directory).")
    parser.add_argument("--schema-json", type=Path, help="Path to the full JSON Schema for the optional offline lexical-cosine retrieval audit.")
    parser.add_argument("--top-k", type=int, default=2, help="Number of retrieved constraint chunks for recall@k (default: 2).")
    parser.add_argument("--out", type=Path, default=Path("lasr_trace_audit_report.json"), help="Output JSON report path.")
    parser.add_argument("--exclude", action="append", default=[], help="Exclude a relative path or filename glob; repeat as needed (e.g. --exclude 'reports/*.json').")
    args = parser.parse_args()

    if not args.root.exists() or not args.root.is_dir():
        print(f"ERROR: --root is not a directory: {args.root}", file=sys.stderr)
        return 2
    if args.top_k < 1:
        print("ERROR: --top-k must be >= 1", file=sys.stderr)
        return 2

    report = analyze(args.root, args.schema_json, args.top_k, out_path=args.out, exclude_patterns=args.exclude)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Scanned {report['data_files_read']} data files; parsed {report['records_parsed']} records.")
    print("Generated audit reports are excluded automatically. Use --exclude to remove other non-trace JSON/CSV files.")
    if report["api_calls_and_recorded_latency"]:
        print("\nRecorded metrics by arm:")
        for row in report["api_calls_and_recorded_latency"]:
            calls = row["api_calls_counted"] if row["api_calls_counted"] is not None else "TBD"
            p50 = row["local_latency_p50_ms"] if row["local_latency_p50_ms"] is not None else "TBD"
            p99 = row["local_latency_p99_ms"] if row["local_latency_p99_ms"] is not None else "TBD"
            print(f"  {row['arm']}: API calls={calls}; recorded local latency p50/p99={p50}/{p99} ms; samples={row['local_latency_samples']}")
    else:
        print("\nAPI-call counts/local AST latency: TBD (no unambiguous matching fields found).")
    rag = report["offline_cosine_rag"]
    print(f"\nOffline cosine RAG status: {rag.get('status')}")
    if rag.get("status") == "computed":
        print(f"  Method: {rag['method']}")
        print(f"  Tasks={rag['tasks_evaluated']}; recall@{rag['k']} macro={rag['macro_recall_at_k']}; micro={rag['micro_recall_at_k']}")
    else:
        print(f"  {rag.get('reason')}")
    print(f"\nReport written to: {args.out}")
    print("NOTE: Missing metrics remain TBD; the script does not fabricate measurements.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
