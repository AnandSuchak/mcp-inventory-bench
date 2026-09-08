"""
Baseline Agent: Direct Function Calling (Monolithic Harness)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Simulates the traditional direct tool-calling architecture:
- Static tool definitions hardcoded into the agent context
- Direct Python API calls to inventory database without MCP abstraction layer
- Measures execution latency, token footprint, and determinism
"""

import sys
import time
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools.inventory_tools import (
    query_low_stock_items,
    compute_product_sales_velocity,
    get_product_supplier_terms,
    create_purchase_order,
    log_agent_audit_event,
)

class DirectInventoryAgent:
    """Baseline agent executing direct in-process database tool calls."""

    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or f"direct-agent-{uuid.uuid4().hex[:6]}"
        self.harness_type = "direct_api"

    def run_replenishment_workflow(self, warehouse_code: str = "WH-US-EAST") -> Dict[str, Any]:
        """
        Closed-loop replenishment workflow:
        1. Check low stock items
        2. Compute sales velocity for affected SKU
        3. Identify best supplier
        4. Create and commit purchase order
        5. Log audit event
        """
        start_time = time.perf_counter()
        tool_call_times = []
        token_estimate = {
            "prompt_tokens": 1450,    # Static prompt tokens with embedded hardcoded schemas
            "completion_tokens": 320   # Response generation tokens
        }

        # Step 1: Query Low Stock
        t0 = time.perf_counter()
        low_stock = query_low_stock_items(warehouse_code)
        t_low_stock = (time.perf_counter() - t0) * 1000
        tool_call_times.append({"tool": "query_low_stock_items", "latency_ms": t_low_stock})

        if not low_stock:
            total_duration = (time.perf_counter() - start_time) * 1000
            return {
                "agent_id": self.agent_id,
                "status": "no_action_needed",
                "total_duration_ms": total_duration,
                "tool_call_times": tool_call_times,
                "tokens": token_estimate,
                "purchase_order": None
            }

        # Pick the most critical low-stock item
        critical_item = low_stock[0]
        product_id = critical_item["product_id"]
        warehouse_id = critical_item["warehouse_id"]
        reorder_point = critical_item["reorder_point"]
        target_stock = critical_item["target_stock"]
        available_qty = critical_item["available_quantity"]

        # Step 2: Compute Velocity
        t1 = time.perf_counter()
        velocity_info = compute_product_sales_velocity(product_id, days=30)
        t_velocity = (time.perf_counter() - t1) * 1000
        tool_call_times.append({"tool": "compute_sales_velocity", "latency_ms": t_velocity})

        # Step 3: Get Supplier Terms
        t2 = time.perf_counter()
        suppliers = get_product_supplier_terms(product_id)
        t_supplier = (time.perf_counter() - t2) * 1000
        tool_call_times.append({"tool": "get_supplier_terms", "latency_ms": t_supplier})

        if not suppliers:
            total_duration = (time.perf_counter() - start_time) * 1000
            return {
                "agent_id": self.agent_id,
                "status": "error_no_supplier",
                "total_duration_ms": total_duration,
                "tool_call_times": tool_call_times,
                "tokens": token_estimate,
                "purchase_order": None
            }

        chosen_supplier = suppliers[0] # primary supplier
        lead_time = chosen_supplier["lead_time_days"]
        daily_burn = velocity_info["daily_sales_velocity"]
        
        # Dynamic order quantity calculation: (Target - Available) + (LeadTime * DailyVelocity)
        recommended_qty = max(
            chosen_supplier["minimum_order_quantity"],
            int((target_stock - available_qty) + (lead_time * daily_burn))
        )

        # Step 4: Issue Purchase Order
        t3 = time.perf_counter()
        po_res = create_purchase_order(
            supplier_id=chosen_supplier["supplier_id"],
            warehouse_id=warehouse_id,
            items=[{
                "product_id": product_id,
                "quantity": recommended_qty,
                "unit_cost": chosen_supplier["contract_unit_cost"]
            }],
            issued_by=self.agent_id,
            notes="Direct Baseline Agent closed-loop replenishment"
        )
        t_po = (time.perf_counter() - t3) * 1000
        tool_call_times.append({"tool": "create_purchase_order", "latency_ms": t_po})

        # Step 5: Audit Log
        t4 = time.perf_counter()
        total_duration = (time.perf_counter() - start_time) * 1000
        log_agent_audit_event(
            agent_id=self.agent_id,
            harness_type=self.harness_type,
            action_type="PO_SUBMITTED",
            target_entity="purchase_orders",
            target_id=po_res["purchase_order_id"],
            payload={"po_number": po_res["po_number"], "total_cost": po_res["total_cost"]},
            reasoning_summary=f"Direct agent triggered replenishment for SKU {critical_item['sku']}. Available: {available_qty}, Ordered: {recommended_qty}.",
            execution_duration_ms=total_duration,
            prompt_tokens=token_estimate["prompt_tokens"],
            completion_tokens=token_estimate["completion_tokens"]
        )
        t_audit = (time.perf_counter() - t4) * 1000
        tool_call_times.append({"tool": "log_audit_event", "latency_ms": t_audit})

        return {
            "agent_id": self.agent_id,
            "status": "success",
            "total_duration_ms": total_duration,
            "tool_call_times": tool_call_times,
            "tokens": token_estimate,
            "purchase_order": po_res
        }

if __name__ == "__main__":
    agent = DirectInventoryAgent()
    result = agent.run_replenishment_workflow()
    print("[+] Direct Agent Execution Result:")
    print(json.dumps(result, indent=2))
