-- TechHub PostgreSQL Schema
-- Run this ONCE to create tables before migrating data from SQLite.
--
-- Usage:
--   psql $DATABASE_URL -f data/migrations/schema.sql

CREATE TABLE IF NOT EXISTS customers (
    customer_id  TEXT PRIMARY KEY,
    email        TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    segment      TEXT NOT NULL  -- Consumer | Corporate | Home Office
);

CREATE TABLE IF NOT EXISTS products (
    product_id   TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    category     TEXT NOT NULL,
    price        NUMERIC(10, 2) NOT NULL,
    in_stock     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL REFERENCES customers(customer_id),
    status          TEXT NOT NULL,
    order_date      DATE NOT NULL,
    shipped_date    DATE,
    tracking_number TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id  TEXT PRIMARY KEY,
    order_id       TEXT NOT NULL REFERENCES orders(order_id),
    product_id     TEXT NOT NULL REFERENCES products(product_id),
    quantity       INTEGER NOT NULL,
    price_per_unit NUMERIC(10, 2) NOT NULL
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
