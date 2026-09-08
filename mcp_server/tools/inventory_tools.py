"""
Inventory Business Tools Implementation for MCP Server and Direct Baseline
Project: mcp-inventory-bench
Author: Anand S. Suchak
"""

import sqlite3
import uuid
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

DB_PATH = Path(__file__).parent.parent.parent / "db" / "inventory.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def list_inventory_tables() -> List[str]:
    """List all available database tables for schema exploration."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        return [row["name"] for row in cur.fetchall()]
    finally:
        conn.close()

def describe_inventory_table(table_name: str) -> List[Dict[str, Any]]:
    """Describe columns, types, and primary keys for a specified table."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name});")
        return [
            {
                "column_id": row["cid"],
                "name": row["name"],
                "data_type": row["type"],
                "not_null": bool(row["notnull"]),
                "is_primary_key": bool(row["pk"])
            }
            for row in cur.fetchall()
        ]
    finally:
        conn.close()

def query_low_stock_items(warehouse_code: Optional[str] = None) -> List[Dict[str, Any]]:
    """Find inventory items below or at their reorder point."""
    conn = get_db()
    try:
        cur = conn.cursor()
        sql = """
            SELECT 
                p.id as product_id,
                p.sku,
                p.name as product_name,
                p.reorder_point,
                p.safety_stock,
                p.target_stock,
                w.id as warehouse_id,
                w.code as warehouse_code,
                i.on_hand_quantity,
                i.reserved_quantity,
                (i.on_hand_quantity - i.reserved_quantity) as available_quantity
            FROM inventory_levels i
            JOIN products p ON i.product_id = p.id
            JOIN warehouses w ON i.warehouse_id = w.id
            WHERE (i.on_hand_quantity - i.reserved_quantity) <= p.reorder_point
        """
        params = []
        if warehouse_code:
            sql += " AND w.code = ?"
            params.append(warehouse_code)
            
        sql += " ORDER BY (i.on_hand_quantity - i.reserved_quantity) ASC"
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def compute_product_sales_velocity(product_id: str, days: int = 30) -> Dict[str, Any]:
    """Compute average daily sales velocity and sales order frequency."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                COALESCE(SUM(quantity), 0) as total_units_sold,
                COUNT(DISTINCT order_id) as total_orders
            FROM sales_order_items
            WHERE product_id = ?
            """,
            (product_id,),
        )
        row = cur.fetchone()
        units = row["total_units_sold"]
        daily_rate = round(units / max(1, days), 2)
        return {
            "product_id": product_id,
            "period_days": days,
            "total_units_sold": units,
            "total_orders": row["total_orders"],
            "daily_sales_velocity": daily_rate
        }
    finally:
        conn.close()

def get_product_supplier_terms(product_id: str) -> List[Dict[str, Any]]:
    """Get active suppliers, negotiated pricing, MOQs, and lead times for a product."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                s.id as supplier_id,
                s.code as supplier_code,
                s.name as supplier_name,
                s.contact_email,
                s.reliability_rating,
                ps.contract_unit_cost,
                ps.lead_time_days,
                s.minimum_order_quantity,
                ps.is_primary
            FROM product_suppliers ps
            JOIN suppliers s ON ps.supplier_id = s.id
            WHERE ps.product_id = ?
            ORDER BY ps.is_primary DESC, ps.contract_unit_cost ASC
            """,
            (product_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def create_purchase_order(
    supplier_id: str,
    warehouse_id: str,
    items: List[Dict[str, Any]],
    issued_by: str = "autonomous-agent",
    notes: str = ""
) -> Dict[str, Any]:
    """
    Create and commit a purchase order.
    `items` format: [{"product_id": str, "quantity": int, "unit_cost": float}]
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        po_id = str(uuid.uuid4())
        po_number = f"PO-AUTO-{uuid.uuid4().hex[:8].upper()}"
        total_cost = sum(item["quantity"] * item["unit_cost"] for item in items)

        cur.execute(
            """INSERT INTO purchase_orders 
               (id, po_number, supplier_id, warehouse_id, status, total_cost, issued_by, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (po_id, po_number, supplier_id, warehouse_id, "submitted", round(total_cost, 2), issued_by, notes),
        )

        for itm in items:
            item_id = str(uuid.uuid4())
            item_cost = round(itm["quantity"] * itm["unit_cost"], 2)
            cur.execute(
                """INSERT INTO purchase_order_items
                   (id, purchase_order_id, product_id, quantity, unit_cost, total_cost)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (item_id, po_id, itm["product_id"], itm["quantity"], itm["unit_cost"], item_cost),
            )

        conn.commit()
        return {
            "status": "success",
            "purchase_order_id": po_id,
            "po_number": po_number,
            "total_cost": round(total_cost, 2),
            "line_items_count": len(items)
        }
    finally:
        conn.close()

def log_agent_audit_event(
    agent_id: str,
    harness_type: str,
    action_type: str,
    target_entity: str,
    target_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    reasoning_summary: Optional[str] = None,
    execution_duration_ms: float = 0.0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> str:
    """Log an agent action to the immutable audit trail."""
    conn = get_db()
    try:
        cur = conn.cursor()
        audit_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO audit_logs 
               (id, agent_id, harness_type, action_type, target_entity, target_id, payload, reasoning_summary, execution_duration_ms, prompt_tokens, completion_tokens)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                audit_id,
                agent_id,
                harness_type,
                action_type,
                target_entity,
                target_id,
                json.dumps(payload or {}),
                reasoning_summary or "",
                execution_duration_ms,
                prompt_tokens,
                completion_tokens,
            ),
        )
        conn.commit()
        return audit_id
    finally:
        conn.close()
