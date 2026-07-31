import sqlite3

def init_db():
    conn = sqlite3.connect("ecommerce_ops.db")
    cursor = conn.cursor()

    # Create Abandoned Carts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS abandoned_carts (
            cart_id TEXT PRIMARY KEY,
            user_id TEXT,
            items_count INTEGER,
            total_value REAL,
            abandoned_hours_ago REAL,
            status TEXT
        )
    """)

    # Create Orders Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            amount REAL,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recovery_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cart_id TEXT,
        customer_email TEXT,
        status TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Populate sample data if empty
    cursor.execute("SELECT COUNT(*) FROM abandoned_carts")
    if cursor.fetchone()[0] == 0:
        carts = [
            ('CART_101', 'USR_501', 3, 149.99, 4.5, 'pending'),
            ('CART_102', 'USR_502', 1, 49.50, 12.0, 'pending'),
            ('CART_103', 'USR_503', 5, 320.00, 2.0, 'pending'),
            ('CART_104', 'USR_504', 2, 85.00, 26.0, 'expired'),
        ]
        cursor.executemany("INSERT INTO abandoned_carts VALUES (?, ?, ?, ?, ?, ?)", carts)

    cursor.execute("SELECT COUNT(*) FROM orders")
    if cursor.fetchone()[0] == 0:
        orders = [
            ('ORD_901', 'USR_501', 120.00, 'completed'),
            ('ORD_902', 'USR_505', 85.50, 'completed'),
            ('ORD_903', 'USR_506', 210.00, 'refunded'),
            ('ORD_904', 'USR_507', 45.00, 'completed'),
        ]
        cursor.executemany("INSERT INTO orders (order_id, customer_id, amount, status) VALUES (?, ?, ?, ?)", orders)

    conn.commit()
    conn.close()
    print("Database 'ecommerce_ops.db' initialized successfully.")

if __name__ == "__main__":
    init_db()
