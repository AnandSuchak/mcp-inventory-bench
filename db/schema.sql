-- ==============================================================================
-- Enterprise Inventory Relational Schema (PostgreSQL & SQLite Compatible DDL)
-- Project: mcp-inventory-bench (Research Paper 2)
-- Author: Anand S. Suchak
-- ==============================================================================

-- 1. Warehouses / Fulfillment Centers
CREATE TABLE IF NOT EXISTS warehouses (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    region VARCHAR(64) NOT NULL,
    address TEXT,
    capacity_sqft INTEGER DEFAULT 100000,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Product Categories
CREATE TABLE IF NOT EXISTS product_categories (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Products (SKUs)
CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(36) PRIMARY KEY,
    sku VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category_id VARCHAR(36) REFERENCES product_categories(id),
    unit_cost DECIMAL(10, 2) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    reorder_point INTEGER NOT NULL DEFAULT 50,
    safety_stock INTEGER NOT NULL DEFAULT 20,
    target_stock INTEGER NOT NULL DEFAULT 200,
    status VARCHAR(32) DEFAULT 'active', -- active, discontinued, seasonal
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Inventory Levels (Per SKU per Warehouse)
CREATE TABLE IF NOT EXISTS inventory_levels (
    id VARCHAR(36) PRIMARY KEY,
    product_id VARCHAR(36) NOT NULL REFERENCES products(id),
    warehouse_id VARCHAR(36) NOT NULL REFERENCES warehouses(id),
    on_hand_quantity INTEGER NOT NULL DEFAULT 0,
    reserved_quantity INTEGER NOT NULL DEFAULT 0,
    allocated_quantity INTEGER NOT NULL DEFAULT 0,
    last_counted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_product_warehouse UNIQUE (product_id, warehouse_id)
);

-- 5. Suppliers / Vendors
CREATE TABLE IF NOT EXISTS suppliers (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    contact_email VARCHAR(128) NOT NULL,
    lead_time_days INTEGER NOT NULL DEFAULT 7,
    minimum_order_quantity INTEGER NOT NULL DEFAULT 10,
    reliability_rating DECIMAL(3, 2) DEFAULT 0.95, -- 0.00 to 1.00 score
    is_preferred BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Product-Supplier Contracts (Catalog pricing and terms)
CREATE TABLE IF NOT EXISTS product_suppliers (
    id VARCHAR(36) PRIMARY KEY,
    product_id VARCHAR(36) NOT NULL REFERENCES products(id),
    supplier_id VARCHAR(36) NOT NULL REFERENCES suppliers(id),
    contract_unit_cost DECIMAL(10, 2) NOT NULL,
    lead_time_days INTEGER NOT NULL DEFAULT 7,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_product_supplier UNIQUE (product_id, supplier_id)
);

-- 7. Sales Orders (Historical and inbound demand)
CREATE TABLE IF NOT EXISTS sales_orders (
    id VARCHAR(36) PRIMARY KEY,
    order_number VARCHAR(64) NOT NULL UNIQUE,
    customer_name VARCHAR(128) NOT NULL,
    order_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(32) NOT NULL DEFAULT 'completed', -- pending, completed, cancelled
    total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Sales Order Line Items (Granular sales velocity tracking)
CREATE TABLE IF NOT EXISTS sales_order_items (
    id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL REFERENCES sales_orders(id),
    product_id VARCHAR(36) NOT NULL REFERENCES products(id),
    warehouse_id VARCHAR(36) NOT NULL REFERENCES warehouses(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Purchase Orders (Issued autonomously by AI agents or human operators)
CREATE TABLE IF NOT EXISTS purchase_orders (
    id VARCHAR(36) PRIMARY KEY,
    po_number VARCHAR(64) NOT NULL UNIQUE,
    supplier_id VARCHAR(36) NOT NULL REFERENCES suppliers(id),
    warehouse_id VARCHAR(36) NOT NULL REFERENCES warehouses(id),
    status VARCHAR(32) NOT NULL DEFAULT 'draft', -- draft, submitted, approved, fulfilled, cancelled
    total_cost DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    issued_by VARCHAR(64) NOT NULL DEFAULT 'agent-autonomous', -- 'agent-autonomous' or operator ID
    expected_delivery_date TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Purchase Order Items
CREATE TABLE IF NOT EXISTS purchase_order_items (
    id VARCHAR(36) PRIMARY KEY,
    purchase_order_id VARCHAR(36) NOT NULL REFERENCES purchase_orders(id),
    product_id VARCHAR(36) NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    total_cost DECIMAL(12, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Agent Action Audit Logs (Traceability and compliance)
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,
    harness_type VARCHAR(32) NOT NULL, -- 'mcp' or 'direct_api'
    action_type VARCHAR(64) NOT NULL,  -- 'STOCK_CHECK', 'VELOCITY_CALC', 'PO_CREATED', 'PO_SUBMITTED'
    target_entity VARCHAR(64) NOT NULL,
    target_id VARCHAR(64),
    payload JSON,
    reasoning_summary TEXT,
    execution_duration_ms DECIMAL(10, 2),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for high-throughput velocity calculations and low-stock queries
CREATE INDEX IF NOT EXISTS idx_inv_product_wh ON inventory_levels(product_id, warehouse_id);
CREATE INDEX IF NOT EXISTS idx_sales_items_prod_date ON sales_order_items(product_id, created_at);
CREATE INDEX IF NOT EXISTS idx_po_supplier ON purchase_orders(supplier_id);
CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_logs(agent_id, action_type);
