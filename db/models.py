"""
Enterprise Inventory Database Models and Access Layer
Project: mcp-inventory-bench
Author: Anand S. Suchak
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).parent / "inventory.db"

def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_table_names(conn: Optional[sqlite3.Connection] = None) -> List[str]:
    """Retrieve all user table names in the database."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row["name"] for row in cur.fetchall()]
        return tables
    finally:
        if should_close:
            conn.close()

def get_table_schema(table_name: str, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Retrieve column specifications for a specific table."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name});")
        columns = [
            {
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "notnull": bool(row["notnull"]),
                "dflt_value": row["dflt_value"],
                "pk": bool(row["pk"])
            }
            for row in cur.fetchall()
        ]
        return columns
    finally:
        if should_close:
            conn.close()

def find_low_stock_items(warehouse_code: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Find products where (on_hand_quantity - reserved_quantity) <= reorder_point."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    try:
        cur = conn.cursor()
        query = """
            SELECT 
                p.id as product_id,
                p.sku,
                p.name as product_name,
                p.reorder_point,
                p.safety_stock,
                p.target_stock,
                w.id as warehouse_id,
                w.code as warehouse_code,
                w.name as warehouse_name,
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
            query += " AND w.code = ?"
            params.append(warehouse_code)
            
        query += " ORDER BY (i.on_hand_quantity - i.reserved_quantity) ASC"
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        if should_close:
            conn.close()

def calculate_product_velocity(product_id: str, days: int = 30, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Calculate historical sales velocity (daily burn rate) for a given product."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
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
        units_sold = row["total_units_sold"]
        daily_velocity = round(units_sold / max(1, days), 2)
        return {
            "product_id": product_id,
            "period_days": days,
            "total_units_sold": units_sold,
            "total_orders": row["total_orders"],
            "average_daily_velocity": daily_velocity
        }
    finally:
        if should_close:
            conn.close()

def get_qualified_suppliers(product_id: str, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Retrieve suppliers contracted for a given product."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
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
        if should_close:
            conn.close()
