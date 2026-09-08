"""
Concurrent Benchmark Runner for MCP vs. Direct Baseline Agents
Project: mcp-inventory-bench
Author: Anand S. Suchak

Executes multi-agent closed-loop workflows across increasing concurrency levels
and records high-precision telemetry.
"""

import sys
import time
import json
import argparse
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).parent.parent))

from baseline.direct_agent import DirectInventoryAgent
from agent_mcp.mcp_agent import MCPInventoryAgent
from mcp_server.server import InventoryMCPServer
from benchmark.metrics_collector import MetricsCollector

RESULTS_DIR = Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def run_single_agent_direct(agent_idx: int) -> dict:
    agent = DirectInventoryAgent(agent_id=f"direct-{agent_idx}")
    return agent.run_replenishment_workflow()

def run_single_agent_mcp(agent_idx: int, server: InventoryMCPServer) -> dict:
    agent = MCPInventoryAgent(mcp_server=server, agent_id=f"mcp-{agent_idx}")
    return agent.run_replenishment_workflow()

def execute_concurrent_benchmark(harness_type: str, concurrency: int, total_requests: int) -> dict:
    """Run concurrent benchmark using ThreadPoolExecutor for realistic thread preemption."""
    print(f"\n========================================================")
    print(f"[*] Benchmarking: {harness_type.upper()} | Concurrency: {concurrency} | Requests: {total_requests}")
    print(f"========================================================")

    server = InventoryMCPServer() if harness_type == "mcp" else None
    t_start = time.perf_counter()
    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(total_requests):
            if harness_type == "mcp":
                f = executor.submit(run_single_agent_mcp, i, server)
            else:
                f = executor.submit(run_single_agent_direct, i)
            futures.append(f)

        for future in futures:
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                results.append({"status": "error", "error_message": str(e), "total_duration_ms": 0.0})

    wall_time = time.perf_counter() - t_start
    summary = MetricsCollector.summarize_run(results, wall_time)
    summary["harness_type"] = harness_type
    summary["concurrency"] = concurrency

    print(f"[+] Wall-clock Time: {summary['wall_clock_time_sec']}s | Throughput: {summary['throughput_ops_per_sec']} ops/sec")
    print(f"[+] Success: {summary['successful_runs']}/{summary['total_runs']} | Error Rate: {summary['error_rate_pct']}%")
    lat = summary["e2e_latency_stats"]
    print(f"[+] E2E Latency (ms) -> p50: {lat['p50']}ms | p90: {lat['p90']}ms | p95: {lat['p95']}ms | p99: {lat['p99']}ms | mean: {lat['mean']}ms")
    tok = summary["token_stats"]
    print(f"[+] Token Footprint  -> Prompt: {tok['avg_prompt_tokens']} | Discovery: {tok['avg_discovery_tokens']} | Total: {tok['avg_total_tokens']}")

    return summary

def run_comparative_study(concurrency_levels=[1, 5, 10, 20], runs_per_level=40):
    """Run end-to-end comparative study across concurrency tiers."""
    study_results = {
        "timestamp": time.time(),
        "baseline": {},
        "mcp": {}
    }

    for c in concurrency_levels:
        # Run Baseline
        res_base = execute_concurrent_benchmark("direct", concurrency=c, total_requests=runs_per_level)
        study_results["baseline"][f"c_{c}"] = res_base

        # Run MCP
        res_mcp = execute_concurrent_benchmark("mcp", concurrency=c, total_requests=runs_per_level)
        study_results["mcp"][f"c_{c}"] = res_mcp

    out_file = RESULTS_DIR / "benchmark_comparison.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(study_results, f, indent=2)
    print(f"\n[+] Full comparative results saved to {out_file}")
    return study_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark MCP vs. Direct Agents")
    parser.add_argument("--mode", choices=["single", "compare"], default="single", help="Benchmark mode")
    parser.add_argument("--harness", choices=["direct", "mcp"], default="mcp", help="Harness to test in single mode")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrency level")
    parser.add_argument("--requests", type=int, default=20, help="Total requests to dispatch")

    args = parser.parse_args()

    if args.mode == "compare":
        run_comparative_study()
    else:
        execute_concurrent_benchmark(args.harness, args.concurrency, args.requests)
