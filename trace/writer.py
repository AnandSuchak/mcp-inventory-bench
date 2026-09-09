"""
Trace Dataset Writer and Manifest Manager
Project: mcp-inventory-bench
Author: Anand S. Suchak

Persists raw observational execution traces to JSONL and updates the dataset manifest.
Maintains Dataset A integrity without mixing prediction targets.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from trace.models import Trace

DATASET_A_DIR = Path(__file__).parent.parent / "datasets" / "dataset_a"
TRACES_FILE = DATASET_A_DIR / "raw_traces.jsonl"
MANIFEST_FILE = DATASET_A_DIR / "manifest.json"

class TraceWriter:
    """Manages appending traces and updating manifest.json for Dataset A."""

    def __init__(self, output_dir: Path = DATASET_A_DIR):
        self.output_dir = output_dir
        self.traces_file = output_dir / "raw_traces.jsonl"
        self.manifest_file = output_dir / "manifest.json"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def append_trace(self, trace: Trace) -> None:
        """Append a single Trace record to raw_traces.jsonl."""
        line = json.dumps(trace.to_dict()) + "\n"
        with open(self.traces_file, "a", encoding="utf-8") as f:
            f.write(line)
        self._update_manifest(trace)

    def write_traces_batch(self, traces: List[Trace]) -> None:
        """Write a batch of Trace records."""
        with open(self.traces_file, "a", encoding="utf-8") as f:
            for t in traces:
                f.write(json.dumps(t.to_dict()) + "\n")
        self.refresh_manifest()

    def _update_manifest(self, latest_trace: Trace) -> None:
        """Incrementally update or regenerate manifest.json."""
        manifest = self.read_manifest()
        manifest["total_traces"] += 1
        
        cat = latest_trace.category
        manifest["categories"][cat] = manifest["categories"].get(cat, 0) + 1

        outcome = latest_trace.final_outcome
        manifest["outcomes"][outcome] = manifest["outcomes"].get(outcome, 0) + 1

        attempts_cnt = len(latest_trace.attempts)
        manifest["total_attempts"] += attempts_cnt
        manifest["total_schema_tokens_exposed"] += latest_trace.total_schema_tokens_exposed

        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def read_manifest(self) -> Dict[str, Any]:
        """Read existing manifest or create default."""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        return {
            "dataset_name": "Dataset A: Observational Execution Traces",
            "schema_version": "2026-07-28/draft-2020-12",
            "total_traces": 0,
            "total_attempts": 0,
            "total_schema_tokens_exposed": 0,
            "categories": {},
            "outcomes": {},
            "models_evaluated": []
        }

    def refresh_manifest(self) -> Dict[str, Any]:
        """Scan raw_traces.jsonl from scratch and compute authoritative manifest metrics."""
        manifest = self.read_manifest()
        if not self.traces_file.exists():
            return manifest

        total = 0
        total_attempts = 0
        total_tokens = 0
        cats: Dict[str, int] = {}
        outcomes: Dict[str, int] = {}
        models = set()

        with open(self.traces_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                total += 1
                cat = data.get("category", "General")
                cats[cat] = cats.get(cat, 0) + 1
                out = data.get("final_outcome", "UNKNOWN")
                outcomes[out] = outcomes.get(out, 0) + 1
                total_attempts += len(data.get("attempts", []))
                total_tokens += data.get("total_schema_tokens_exposed", 0)
                if "model" in data:
                    models.add(data["model"])

        manifest["total_traces"] = total
        manifest["total_attempts"] = total_attempts
        manifest["total_schema_tokens_exposed"] = total_tokens
        manifest["categories"] = cats
        manifest["outcomes"] = outcomes
        manifest["models_evaluated"] = sorted(list(models))

        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        return manifest
