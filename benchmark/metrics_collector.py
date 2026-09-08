"""
Benchmark Metrics and Telemetry Collector
Project: mcp-inventory-bench
Author: Anand S. Suchak

Calculates statistical distributions for latency percentiles (p50, p90, p95, p99),
token economics, error rates, and throughput.
"""

import math
from typing import List, Dict, Any

class MetricsCollector:
    """Statistical collector for agent benchmark evaluations."""

    @staticmethod
    def calculate_percentiles(latencies: List[float]) -> Dict[str, float]:
        """Compute p50, p90, p95, p99, mean, and stdev for a series of latencies."""
        if not latencies:
            return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "std": 0.0, "count": 0}

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        def percentile(p: float) -> float:
            k = (n - 1) * (p / 100.0)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_latencies[int(k)]
            d0 = sorted_latencies[int(f)] * (c - k)
            d1 = sorted_latencies[int(c)] * (k - f)
            return d0 + d1

        mean_val = sum(latencies) / n
        variance = sum((x - mean_val) ** 2 for x in latencies) / max(1, n - 1)
        std_val = math.sqrt(variance)

        return {
            "count": n,
            "p50": round(percentile(50), 2),
            "p90": round(percentile(90), 2),
            "p95": round(percentile(95), 2),
            "p99": round(percentile(99), 2),
            "mean": round(mean_val, 2),
            "std": round(std_val, 2),
            "min": round(sorted_latencies[0], 2),
            "max": round(sorted_latencies[-1], 2),
        }

    @staticmethod
    def summarize_run(results: List[Dict[str, Any]], wall_time_sec: float) -> Dict[str, Any]:
        """Aggregate run results into a complete benchmark report."""
        total_runs = len(results)
        successful_runs = [r for r in results if r.get("status") == "success"]
        error_runs = [r for r in results if r.get("status") != "success"]

        total_latencies = [r["total_duration_ms"] for r in successful_runs]
        
        # Token metrics
        prompt_tokens = [r["tokens"]["prompt_tokens"] for r in successful_runs]
        completion_tokens = [r["tokens"]["completion_tokens"] for r in successful_runs]
        discovery_tokens = [r["tokens"].get("discovery_tokens", 0) for r in successful_runs]

        # Break down per-tool latencies
        tool_latencies: Dict[str, List[float]] = {}
        for r in successful_runs:
            for step in r.get("tool_call_times", []):
                t_name = step["tool"]
                if t_name not in tool_latencies:
                    tool_latencies[t_name] = []
                tool_latencies[t_name].append(step["latency_ms"])

        per_tool_stats = {
            t_name: MetricsCollector.calculate_percentiles(l_list)
            for t_name, l_list in tool_latencies.items()
        }

        throughput = round(total_runs / max(0.001, wall_time_sec), 2)
        error_rate = round((len(error_runs) / max(1, total_runs)) * 100, 2)

        return {
            "total_runs": total_runs,
            "successful_runs": len(successful_runs),
            "error_runs": len(error_runs),
            "error_rate_pct": error_rate,
            "wall_clock_time_sec": round(wall_time_sec, 3),
            "throughput_ops_per_sec": throughput,
            "e2e_latency_stats": MetricsCollector.calculate_percentiles(total_latencies),
            "token_stats": {
                "avg_prompt_tokens": round(sum(prompt_tokens) / max(1, len(prompt_tokens)), 1),
                "avg_discovery_tokens": round(sum(discovery_tokens) / max(1, len(discovery_tokens)), 1),
                "avg_completion_tokens": round(sum(completion_tokens) / max(1, len(completion_tokens)), 1),
                "avg_total_tokens": round(
                    (sum(prompt_tokens) + sum(discovery_tokens) + sum(completion_tokens)) / max(1, len(prompt_tokens)), 1
                ),
            },
            "per_tool_latency_stats": per_tool_stats
        }
