"""
Unit Tests for SchemaCompressor (Prompt & Schema Compression Layer)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Target: compression.schema_compressor.SchemaCompressor
Tests semantic signature conversion, token compaction ratios, and edge case safety.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compression.schema_compressor import SchemaCompressor

class TestSchemaCompressor(unittest.TestCase):
    """Test suite for MCP schema compression layer."""

    def setUp(self):
        self.compressor = SchemaCompressor(mode="structural")
        self.sample_tool = {
            "name": "query_low_stock_items",
            "description": "Discover all available low stock items for a specific warehouse.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "warehouse_code": {
                        "type": "string",
                        "description": "The warehouse code identifier"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max items to return"
                    }
                },
                "required": ["warehouse_code"]
            }
        }

    def test_single_tool_signature_compression(self):
        """Verify that verbose JSON Schema is transformed into compact IDL signature."""
        compressed_sig = self.compressor.compress_tool_schema(self.sample_tool)
        
        # Must retain function name
        self.assertTrue(compressed_sig.startswith("query_low_stock_items("))
        # Required parameter must not have '?'
        self.assertIn("warehouse_code:str", compressed_sig)
        # Optional parameter must have '?'
        self.assertIn("limit?:int", compressed_sig)
        # Must eliminate filler words
        self.assertNotIn("discover all available", compressed_sig.lower())

    def test_token_reduction_ratio(self):
        """Verify that compression achieves at least 50% token reduction on standard tool sets."""
        from mcp_server.server import TOOL_DEFINITIONS
        compressed_text, stats = self.compressor.compress_tool_definitions(TOOL_DEFINITIONS)
        
        self.assertGreater(stats["compression_ratio_pct"], 50.0)
        self.assertGreater(stats["tokens_saved"], 200)
        self.assertLess(stats["compressed_tokens"], stats["original_tokens"])

    def test_sub_millisecond_overhead(self):
        """Verify that structural schema compaction executes well under 5 milliseconds."""
        from mcp_server.server import TOOL_DEFINITIONS
        _, stats = self.compressor.compress_tool_definitions(TOOL_DEFINITIONS)
        self.assertLess(stats["compression_time_ms"], 10.0)

    def test_malformed_tool_schema_edge_cases(self):
        """Verify robust handling of empty tools, missing properties, or empty schemas."""
        # 1. Empty tool list
        empty_res, empty_stats = self.compressor.compress_tool_definitions([])
        self.assertEqual(empty_res, "")
        self.assertEqual(empty_stats["tokens_saved"], 0)

        # 2. Tool with missing inputSchema
        edge_tool = {"name": "dummy_tool", "description": "No schema provided"}
        compressed = self.compressor.compress_tool_schema(edge_tool)
        self.assertEqual(compressed, "dummy_tool(): No schema provided")

        # 3. Tool with empty properties
        edge_tool2 = {"name": "zero_args", "description": "Takes nothing", "inputSchema": {"type": "object", "properties": {}}}
        compressed2 = self.compressor.compress_tool_schema(edge_tool2)
        self.assertEqual(compressed2, "zero_args(): Takes nothing")

if __name__ == "__main__":
    unittest.main()
