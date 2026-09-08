"""
Enterprise Inventory Database Seeder
Project: mcp-inventory-bench
Author: Anand S. Suchak

Generates realistic parameterized enterprise inventory data:
- Warehouses across regions
- Product categories and SKUs with variable safety stock & velocity
- Dynamic inventory levels (including controlled low-stock and stock-out SKUs)
- Qualified suppliers with MOQ, lead times, and negotiated contracts
- 30-day historical sales orders for velocity computations
"""

import sqlite3
import uuid
import random
import datetime
from pathlib import Path

DB_FILE = Path(__file__).parent / "inventory.db"
SCHEMA_FILE = Path(__file__).parent / "schema.sql"

WAREHOUSES = [
    ("WH-US-EAST", "East Coast Distribution Hub", "North America - East", 150000),
    ("WH-US-WEST", "West Coast Logistics Center", "North America - West", 200000),
    ("WH-EU-CENTRAL", "Frankfurt Fulfillment Center", "Europe - Central", 120000),
    ("WH-APAC-SOUTH", "Singapore Regional Hub", "Asia-Pacific", 180000),
    ("WH-LATAM-NORTH", "Monterrey Distribution Center", "Latin America", 90000),
]

CATEGORIES = [
    "Industrial Electronics",
    "Microcontrollers & Sensors",
    "Precision Fasteners",
    "Pneumatic Actuators",
    "Power Distribution Units",
    "Thermal Management",
    "Fiber Optic Transceivers",
    "Robotic Servos",
]

SUPPLIERS = [
    ("SUP-TEXAS-SEMI", "Texas Semiconductor Ltd", "orders@texassemi.mock", 5, 25, 0.98, True),
    ("SUP-NIPPON-PREC", "Nippon Precision Mechatronics", "b2b@nipponprec.mock", 12, 10, 0.96, True),
    ("SUP-ALPS-OPTO", "Alps Optical Networking", "sales@alpsopto.mock", 8, 15, 0.94, False),
    ("SUP-RHINE-IND", "Rhine Industrial Components AG", "supply@rhineind.mock", 6, 20, 0.99, True),
    ("SUP-GLOBAL-FAST", "Global Fastener Distributors", "fulfillment@globalfast.mock", 3, 100, 0.92, False),
    ("SUP-SHENZHEN-ROBO", "Shenzhen Robotics Supply", "dispatch@shenzhenrobo.mock", 14, 5, 0.89, False),
]

def init_db(db_path: Path = DB_FILE) -> sqlite3.Connection:
    """Initialize database from schema.sql."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema_ddl = f.read()
    
    # SQLite compatibility adjustment for standard DDL
    statements = [stmt.strip() for stmt in schema_ddl.split(";") if stmt.strip()]
    with conn:
        for stmt in statements:
            conn.execute(stmt)
    return conn

def seed_database(db_path: Path = DB_FILE, num_products: int = 150, seed: int = 42):
    """Seed synthetic enterprise dataset."""
    random.seed(seed)
    conn = init_db(db_path)
    cur = conn.cursor()

    print(f"[*] Seeding database at {db_path} with seed={seed}...")

    # 1. Warehouses
    warehouse_ids = []
    for code, name, region, capacity in WAREHOUSES:
        w_id = str(uuid.uuid4())
        cur.execute(
            """INSERT OR REPLACE INTO warehouses (id, code, name, region, capacity_sqft)
               VALUES (?, ?, ?, ?, ?)""",
            (w_id, code, name, region, capacity),
        )
        warehouse_ids.append(w_id)

    # 2. Product Categories
    category_ids = []
    for cat_name in CATEGORIES:
        c_id = str(uuid.uuid4())
        cur.execute(
            """INSERT OR REPLACE INTO product_categories (id, name, description)
               VALUES (?, ?, ?)""",
            (c_id, cat_name, f"Enterprise components for {cat_name}"),
        )
        category_ids.append(c_id)

    # 3. Suppliers
    supplier_ids = []
    for code, name, email, lead_time, moq, rating, preferred in SUPPLIERS:
        s_id = str(uuid.uuid4())
        cur.execute(
            """INSERT OR REPLACE INTO suppliers (id, code, name, contact_email, lead_time_days, minimum_order_quantity, reliability_rating, is_preferred)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (s_id, code, name, email, lead_time, moq, rating, preferred),
        )
        supplier_ids.append(s_id)

    # 4. Products & Supplier Contracts
    product_ids = []
    for i in range(1, num_products + 1):
        p_id = str(uuid.uuid4())
        sku = f"SKU-{10000 + i}"
        cat_id = random.choice(category_ids)
        cost = round(random.uniform(5.0, 450.0), 2)
        price = round(cost * random.uniform(1.35, 2.2), 2)
        reorder_pt = random.randint(30, 120)
        safety_stk = random.randint(15, 50)
        target_stk = reorder_pt * random.randint(3, 5)

        cur.execute(
            """INSERT OR REPLACE INTO products (id, sku, name, category_id, unit_cost, unit_price, reorder_point, safety_stock, target_stock, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (p_id, sku, f"Enterprise Spec Component {sku}", cat_id, cost, price, reorder_pt, safety_stk, target_stk, "active"),
        )
        product_ids.append((p_id, cost, reorder_pt, safety_stk, target_stk))

        # Assign 1 or 2 qualified suppliers
        chosen_suppliers = random.sample(supplier_ids, k=min(2, len(supplier_ids)))
        for idx, sup_id in enumerate(chosen_suppliers):
            contract_cost = round(cost * random.uniform(0.92, 1.05), 2)
            cur.execute(
                """INSERT OR REPLACE INTO product_suppliers (id, product_id, supplier_id, contract_unit_cost, lead_time_days, is_primary)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), p_id, sup_id, contract_cost, random.randint(4, 15), idx == 0),
            )

    # 5. Inventory Levels across Warehouses (Include intentionally low stock for testing agent trigger)
    low_stock_target_skus = set(random.sample([p[0] for p in product_ids], k=int(num_products * 0.18))) # ~18% need reordering

    for p_id, cost, reorder_pt, safety_stk, target_stk in product_ids:
        for w_id in warehouse_ids:
            inv_id = str(uuid.uuid4())
            if p_id in low_stock_target_skus and w_id == warehouse_ids[0]:
                # Critical stock trigger
                on_hand = random.randint(2, max(3, reorder_pt // 2))
                reserved = random.randint(0, on_hand // 2)
            else:
                on_hand = random.randint(reorder_pt + 10, target_stk)
                reserved = random.randint(0, on_hand // 5)

            cur.execute(
                """INSERT OR REPLACE INTO inventory_levels (id, product_id, warehouse_id, on_hand_quantity, reserved_quantity, allocated_quantity)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (inv_id, p_id, w_id, on_hand, reserved, 0),
            )

    # 6. Historical Sales Orders & Order Items (Past 30 days)
    now = datetime.datetime.now()
    num_orders = num_products * 6
    for o_idx in range(num_orders):
        order_id = str(uuid.uuid4())
        days_ago = random.uniform(0.5, 30.0)
        order_date = now - datetime.timedelta(days=days_ago)
        order_num = f"SO-2026-{100000 + o_idx}"

        cur.execute(
            """INSERT OR REPLACE INTO sales_orders (id, order_number, customer_name, order_date, status, total_amount)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (order_id, order_num, f"Enterprise Client #{random.randint(100, 999)}", order_date.strftime("%Y-%m-%d %H:%M:%S"), "completed", 0.0),
        )

        # 1 to 4 items per order
        order_total = 0.0
        items_count = random.randint(1, 4)
        sampled_products = random.sample(product_ids, k=items_count)
        for p_id, cost, _, _, _ in sampled_products:
            wh_id = random.choice(warehouse_ids)
            qty = random.randint(2, 25)
            price = round(cost * 1.5, 2)
            line_cost = qty * price
            order_total += line_cost

            cur.execute(
                """INSERT OR REPLACE INTO sales_order_items (id, order_id, product_id, warehouse_id, quantity, unit_price, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), order_id, p_id, wh_id, qty, price, order_date.strftime("%Y-%m-%d %H:%M:%S")),
            )

        cur.execute("UPDATE sales_orders SET total_amount = ? WHERE id = ?", (round(order_total, 2), order_id))

    conn.commit()
    conn.close()
    print(f"[+] Seeding complete! Database ready at {db_path}")

if __name__ == "__main__":
    seed_database()
