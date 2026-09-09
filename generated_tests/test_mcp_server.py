"""
Unit Tests for InventoryMCPServer (JSON-RPC 2.0 Tool Protocol)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Target: mcp_server.server.InventoryMCPServer
Validates JSON-RPC 2.0 compliance, tool listing, execution, and error protocols.
"""

import sys
import json
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.server import InventoryMCPServer, TOOL_DEFINITIONS

class TestInventoryMCPServer(unittest.TestCase):
    """Test suite for Model Context Protocol server."""

    def setUp(self):
        self.server = InventoryMCPServer()

    def test_tools_list_protocol(self):
        """Verify tools/list conforms to Model Context Protocol specification."""
        req = {
            "jsonrpc": "2.0",
            "id": "req-1",
            "method": "tools/list",
            "params": {}
        }
        resp = self.server.handle_request(req)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], "req-1")
        self.assertIn("result", resp)
        self.assertIn("tools", resp["result"])
        
        tool_names = [t["name"] for t in resp["result"]["tools"]]
        self.assertIn("query_low_stock_items", tool_names)
        self.assertIn("compute_sales_velocity", tool_names)
        self.assertIn("create_purchase_order", tool_names)

    def test_tool_call_execution(self):
        """Verify tools/call executes and returns structured text content."""
        req = {
            "jsonrpc": "2.0",
            "id": "req-2",
            "method": "tools/call",
            "params": {
                "name": "query_low_stock_items",
                "arguments": {"warehouse_code": "WH-US-EAST"}
            }
        }
        resp = self.server.handle_request(req)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertIn("result", resp)
        self.assertFalse(resp["result"]["isError"])
        
        content = resp["result"]["content"][0]
        self.assertEqual(content["type"], "text")
        data = json.loads(content["text"])
        self.assertIsInstance(data, list)

    def test_unsupported_tool_error(self):
        """Verify -32601 Method not found error for non-existent tools."""
        req = {
            "jsonrpc": "2.0",
            "id": "req-err-1",
            "method": "tools/call",
            "params": {
                "name": "non_existent_tool_xyz",
                "arguments": {}
            }
        }
        resp = self.server.handle_request(req)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_unsupported_jsonrpc_method(self):
        """Verify JSON-RPC error when client sends invalid protocol method."""
        req = {
            "jsonrpc": "2.0",
            "id": "req-err-2",
            "method": "invalid/method_name",
            "params": {}
        }
        resp = self.server.handle_request(req)
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

if __name__ == "__main__":
    unittest.main()
