"""
Integration Tests for Closed-Loop Inventory Replenishment Workflow
Project: mcp-inventory-bench
Author: Anand S. Suchak

Tests Direct Agent, Vanilla MCP Agent, and Compressed MCP Agent executing
closed-loop inventory replenishment, purchase order creation, and audit trails.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from baseline.direct_agent import DirectInventoryAgent
from agent_mcp.mcp_agent import MCPInventoryAgent
from agent_mcp.compressed_mcp_agent import CompressedMCPAgent

class TestClosedLoopReplenishment(unittest.TestCase):
    """Test suite validating end-to-end closed loop replenishment across all 3 architectures."""

    def test_direct_agent_replenishment(self):
        """Verify baseline direct agent executes replenishment successfully."""
        agent = DirectInventoryAgent()
        result = agent.run_replenishment_workflow(warehouse_code="WH-US-EAST")
        
        self.assertEqual(result["status"], "success")
        self.assertIsNotNone(result["purchase_order"])
        self.assertIn("po_number", result["purchase_order"])
        self.assertGreater(result["purchase_order"]["total_cost"], 0)
        self.assertGreater(result["total_duration_ms"], 0)

    def test_vanilla_mcp_agent_replenishment(self):
        """Verify vanilla MCP agent discovers tools and executes replenishment."""
        agent = MCPInventoryAgent()
        result = agent.run_replenishment_workflow(warehouse_code="WH-US-EAST")
        
        self.assertEqual(result["status"], "success")
        self.assertIsNotNone(result["purchase_order"])
        self.assertIn("po_number", result["purchase_order"])
        self.assertEqual(result["tokens"]["discovery_tokens"], 680)

    def test_compressed_mcp_agent_replenishment(self):
        """Verify compressed MCP agent compresses schema and completes replenishment with lower tokens."""
        agent = CompressedMCPAgent()
        result = agent.run_replenishment_workflow(warehouse_code="WH-US-EAST")
        
        self.assertEqual(result["status"], "success")
        self.assertIsNotNone(result["purchase_order"])
        self.assertIn("po_number", result["purchase_order"])
        
        # Verify compression token reduction
        self.assertLess(result["tokens"]["discovery_tokens"], 300)
        self.assertGreater(result["tokens"]["tokens_saved_vs_vanilla"], 400)
        self.assertGreater(result["tokens"]["compression_ratio_pct"], 50.0)

if __name__ == "__main__":
    unittest.main()
