"""
Model Context Protocol (MCP) Server Implementation
Project: mcp-inventory-bench
Author: Anand S. Suchak

Exposes inventory tools and schema inspection over JSON-RPC 2.0.
Supports standard stdio stream and programmatic client invocations.
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools.inventory_tools import (
    list_inventory_tables,
    describe_inventory_table,
    query_low_stock_items,
    compute_product_sales_velocity,
    get_product_supplier_terms,
    create_purchase_order,
    log_agent_audit_event,
)

# Registry of exposed MCP Tools with their JSON schemas
TOOL_DEFINITIONS = [
    {
        "name": "list_tables",
        "description": "Discover all available relational database tables in the enterprise inventory system.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "describe_table",
        "description": "Inspect column names, data types, constraints, and keys for a specific table.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "The exact name of the table to inspect (e.g. 'products', 'inventory_levels', 'suppliers')"
                }
            },
            "required": ["table_name"]
        }
    },
    {
        "name": "query_low_stock_items",
        "description": "Query all product SKUs where available inventory is less than or equal to the reorder point threshold.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "warehouse_code": {
                    "type": "string",
                    "description": "Optional warehouse filter code (e.g. 'WH-US-EAST')"
                }
            },
            "required": []
        }
    },
    {
        "name": "compute_sales_velocity",
        "description": "Compute daily sales velocity and order counts for a product SKU over a historical lookback window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The UUID of the product"
                },
                "days": {
                    "type": "integer",
                    "description": "Lookback window in days (default: 30)",
                    "default": 30
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "get_supplier_terms",
        "description": "Retrieve contracted suppliers, pricing, MOQs, and lead times for replenishment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The UUID of the product"
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "create_purchase_order",
        "description": "Issue an authorized purchase order to replenish stock for a specific warehouse.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "supplier_id": {"type": "string"},
                "warehouse_id": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "unit_cost": {"type": "number"}
                        },
                        "required": ["product_id", "quantity", "unit_cost"]
                    }
                },
                "notes": {"type": "string"}
            },
            "required": ["supplier_id", "warehouse_id", "items"]
        }
    },
    {
        "name": "log_audit_event",
        "description": "Record an immutable audit log entry for traceability and compliance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "harness_type": {"type": "string"},
                "action_type": {"type": "string"},
                "target_entity": {"type": "string"},
                "target_id": {"type": "string"},
                "reasoning_summary": {"type": "string"},
                "execution_duration_ms": {"type": "number"},
                "prompt_tokens": {"type": "integer"},
                "completion_tokens": {"type": "integer"}
            },
            "required": ["agent_id", "harness_type", "action_type", "target_entity"]
        }
    }
]

class InventoryMCPServer:
    """JSON-RPC 2.0 Model Context Protocol compliant Server."""

    def __init__(self):
        self.tools = {
            "list_tables": lambda args: list_inventory_tables(),
            "describe_table": lambda args: describe_inventory_table(args["table_name"]),
            "query_low_stock_items": lambda args: query_low_stock_items(args.get("warehouse_code")),
            "compute_sales_velocity": lambda args: compute_product_sales_velocity(args["product_id"], args.get("days", 30)),
            "get_supplier_terms": lambda args: get_product_supplier_terms(args["product_id"]),
            "create_purchase_order": lambda args: create_purchase_order(
                args["supplier_id"],
                args["warehouse_id"],
                args["items"],
                notes=args.get("notes", "Auto-generated by MCP Agent")
            ),
            "log_audit_event": lambda args: log_agent_audit_event(
                args["agent_id"],
                args["harness_type"],
                args["action_type"],
                args["target_entity"],
                target_id=args.get("target_id"),
                payload=args.get("payload"),
                reasoning_summary=args.get("reasoning_summary"),
                execution_duration_ms=args.get("execution_duration_ms", 0.0),
                prompt_tokens=args.get("prompt_tokens", 0),
                completion_tokens=args.get("completion_tokens", 0),
            )
        }

    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch JSON-RPC 2.0 messages."""
        msg_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params", {})

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": TOOL_DEFINITIONS
                }
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            if tool_name not in self.tools:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method/Tool '{tool_name}' not found"
                    }
                }
            try:
                result = self.tools[tool_name](arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result)
                            }
                        ],
                        "isError": False
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32000,
                        "message": f"Tool execution error: {str(e)}"
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Unsupported JSON-RPC method: {method}"
                }
            }

    async def run_stdio(self):
        """Run MCP server over standard input / output pipes."""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            line = await reader.readline()
            if not line:
                break
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue
            try:
                req = json.loads(line_str)
                resp = self.handle_request(req)
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
            except Exception as err:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(err)}"}
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()

if __name__ == "__main__":
    server = InventoryMCPServer()
    asyncio.run(server.run_stdio())
