# Evaluating the Efficiency of Autonomous AI Agents using Model Context Protocol (MCP) in Closed-Loop Inventory Workflows

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Research: Empirical Study](https://img.shields.io/badge/Research-Empirical%20Benchmark-blue.svg)](#)

> **Author**: Anand S. Suchak  
> *Computer Science Researcher, GTU Alumni, Incoming PhD Candidate*  
> **Repository Slug**: `mcp-agent-eval`

---

## 1. Abstract & Executive Summary

As enterprise systems transition from hardcoded integration pipelines to autonomous agentic architectures, the **Model Context Protocol (MCP)** has emerged as an open standard for securely exposing data schemas and execution tools to Large Language Models (LLMs). While MCP offers unprecedented modularity and decoupling, the practical performance trade-offs—specifically **transport/protocol latency**, **token economy overhead**, **tool-calling determinism under dynamic schema discovery**, and **system throughput under multi-agent concurrency**—remain unquantified in production-like environments.

This repository provides an empirical benchmarking testbed and academic paper evaluating autonomous AI agents tasked with a **closed-loop inventory replenishment workflow** (detecting low stock across multi-tier warehouses based on sales velocity, querying supplier terms, and autonomously issuing purchase orders). We benchmark direct LLM tool-calling (baseline) against MCP client-server architectures across multiple concurrency levels ($N \in \{1, 5, 10, 25, 50, 100\}$).

---

## 2. Core Research Questions (RQs)

- **$RQ_1$ (Latency & Overhead)**: What is the exact tail-latency overhead ($p_{50}, p_{90}, p_{95}, p_{99}$) introduced by MCP JSON-RPC abstraction layers compared to direct database function calling?
- **$RQ_2$ (Token Economy)**: How does dynamic schema reflection and tool specification via MCP influence prompt vs. completion token footprints across multi-turn reasoning cycles?
- **$RQ_3$ (Determinism & Accuracy)**: Does MCP schema encapsulation reduce tool hallucination rates, parameter mismatch, and invalid SQL/tool invocations compared to monolithic system prompting?
- **$RQ_4$ (Concurrency Scalability)**: How do MCP server transports (stdio vs. SSE / HTTP streaming) scale under concurrent agent loads before saturating system memory and I/O?

---

## 3. Project Structure

```text
mcp-agent-eval/
├── db/                         # Relational schema and seed generators
│   ├── schema.sql              # Enterprise inventory DDL (PostgreSQL / SQLite)
│   └── seed_data.py            # Parametric data generator (100-10,000 SKUs, velocity distributions)
├── mcp_server/                 # Model Context Protocol server implementations
│   ├── server.py               # FastMCP / JSON-RPC server exposing schema & tool endpoints
│   └── tools/                  # Inventory, supplier, and order management tools
├── baseline/                   # Baseline harness: Direct API / monolithic tool-calling agent
├── agent_mcp/                  # Treatment harness: Agent dynamically discovering & using MCP tools
├── benchmark/                  # Concurrent benchmark runner & telemetry collectors
│   ├── runner.py               # Async multi-agent workload orchestrator
│   └── metrics_collector.py    # Latency (p50-p99), token counters, and error tracker
├── paper/                      # Academic research paper (LaTeX source files)
│   ├── main.tex
│   ├── sections/
│   └── references.bib
├── results/                    # Benchmark output datasets and generated evaluation figures
└── README.md
```

---

## 4. Getting Started

### Prerequisites
- Python 3.11+
- Git

### Quickstart Setup
```bash
# Clone the repository
git clone https://github.com/AnandSuchak/mcp-agent-eval.git
cd mcp-agent-eval

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 5. Citation

If you use this benchmark testbed or reference our empirical findings, please cite:

```bibtex
@article{suchak2026mcp,
  title={Evaluating the Operational Efficiency, Token Economy, and Determinism of Autonomous AI Agents Using Model Context Protocol in Enterprise Inventory Workflows},
  author={Suchak, Anand S.},
  year={2026},
  journal={arXiv preprint}
}
```

---

## 6. License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
