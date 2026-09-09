"""
Concurrent Benchmark Runner for 3-Way Architecture Evaluation:
1. Direct Baseline Agent
2. Vanilla MCP Agent
3. Compressed MCP Agent (with Prompt/Schema Compression)

Project: mcp-inventory-bench
Author: Anand S. Suchak
"""

import sys
import time
import json
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from baseline.direct_agent import DirectInventoryAgent
from agent_mcp.mcp_agent import MCPInventoryAgent
from agent_mcp.compressed_mcp_agent import CompressedMCPAgent
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

def run_single_agent_mcp_compressed(agent_idx: int, server: InventoryMCPServer) -> dict:
    agent = CompressedMCPAgent(mcp_server=server, agent_id=f"mcp-comp-{agent_idx}")
    return agent.run_replenishment_workflow()

def execute_concurrent_benchmark(harness_type: str, concurrency: int, total_requests: int) -> dict:
    """Run concurrent benchmark using ThreadPoolExecutor for realistic thread preemption."""
    print(f"\n======================================================================")
    print(f"[*] Benchmarking: {harness_type.upper()} | Concurrency: {concurrency} | Requests: {total_requests}")
    print(f"======================================================================")

    server = InventoryMCPServer() if "mcp" in harness_type else None
    t_start = time.perf_counter()
    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(total_requests):
            if harness_type == "mcp":
                f = executor.submit(run_single_agent_mcp, i, server)
            elif harness_type == "mcp_compressed":
                f = executor.submit(run_single_agent_mcp_compressed, i, server)
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
    if "avg_tokens_saved" in tok and tok["avg_tokens_saved"] > 0:
        print(f"[+] Compression      -> Tokens Saved: {tok['avg_tokens_saved']} ({tok['avg_compression_ratio_pct']}%) | Est. TTFT: {tok['estimated_ttft_ms']}ms")

    return summary

def run_3way_comparative_study(concurrency_levels=[1, 5, 10, 20], runs_per_level=30):
    """Run full 3-way comparative evaluation across all architectures and concurrency tiers."""
    study_results = {
        "timestamp": time.time(),
        "baseline_direct": {},
        "vanilla_mcp": {},
        "compressed_mcp": {}
    }

    for c in concurrency_levels:
        print(f"\n>>>>>>>>>>>>>>> EXECUTING CONCURRENCY TIER: N={c} <<<<<<<<<<<<<<<")
        # 1. Baseline Direct Agent
        res_base = execute_concurrent_benchmark("direct", concurrency=c, total_requests=runs_per_level)
        study_results["baseline_direct"][f"c_{c}"] = res_base

        # 2. Vanilla MCP Agent
        res_mcp = execute_concurrent_benchmark("mcp", concurrency=c, total_requests=runs_per_level)
        study_results["vanilla_mcp"][f"c_{c}"] = res_mcp

        # 3. Compressed MCP Agent
        res_comp = execute_concurrent_benchmark("mcp_compressed", concurrency=c, total_requests=runs_per_level)
        study_results["compressed_mcp"][f"c_{c}"] = res_comp

    out_file = RESULTS_DIR / "benchmark_3way_comparison.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(study_results, f, indent=2)
    print(f"\n[+] 3-Way Comparative study complete! Saved to {out_file}")
    return study_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="3-Way Benchmark Runner (Direct vs. Vanilla MCP vs. Compressed MCP)")
    parser.add_argument("--mode", choices=["single", "compare", "compare3"], default="single", help="Benchmark execution mode")
    parser.add_argument("--harness", choices=["direct", "mcp", "mcp_compressed"], default="mcp_compressed", help="Agent harness")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrency level")
    parser.add_argument("--requests", type=int, default=20, help="Total requests to dispatch")

    args = parser.parse_args()

    if args.mode == "compare3":
        run_3way_comparative_study()
    elif args.mode == "compare":
        # standard 2-way comparison
        for c in [1, 5, 10]:
            execute_concurrent_benchmark("direct", c, 20)
            execute_concurrent_benchmark("mcp", c, 20)
    else:
        execute_concurrent_benchmark(args.harness, args.concurrency, args.requests)
