"""
Database migration script — adds new columns to existing tables.
Run this once after updating models with new fields.
"""
import sqlite3
import os

DB_PATH = "storage/calories.db"

if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}. Nothing to migrate.")
    exit(0)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def add_columns_if_missing(table, columns):
    """Add columns to a table if they don't already exist."""
    cursor.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cursor.fetchall()}
    for col, dtype in columns.items():
        if col not in existing:
            sql = f'ALTER TABLE {table} ADD COLUMN {col} {dtype}'
            cursor.execute(sql)
            print(f"  + {table}.{col} ({dtype})")

print("Migrating users table...")
add_columns_if_missing("users", {
    "subscription_status": "VARCHAR DEFAULT 'free'",
    "subscription_plan": "VARCHAR DEFAULT ''",
    "subscription_expiry": "DATETIME",
    "stripe_customer_id": "VARCHAR DEFAULT ''",
    "stripe_subscription_id": "VARCHAR DEFAULT ''",
    "license_type": "VARCHAR DEFAULT 'free'",
    "license_purchased_at": "DATETIME",
    "remaining_daily_recognitions": "INTEGER DEFAULT 10",
    "is_admin": "BOOLEAN DEFAULT 0",
    "is_active": "BOOLEAN DEFAULT 1",
    "updated_at": "DATETIME",
})

# Check new tables exist
print("\nChecking new tables...")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = {row[0] for row in cursor.fetchall()}
expected_tables = {"invoices", "ad_logs", "admin_users", "system_config", "audit_logs", "model_monitor"}
missing = expected_tables - tables
if missing:
    print(f"  New tables will be created by SQLAlchemy: {missing}")
else:
    print("  All new tables exist.")

conn.commit()
conn.close()
print("\nMigration complete!")
