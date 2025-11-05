import sys
sys.stdout.reconfigure(encoding='utf-8')
import pyodbc

# ----------------- DB CONNECTION -----------------
def connect_to_db():
    """Connect to SQL Server using Windows Authentication."""
    try:
        conn = pyodbc.connect(
            'Driver={SQL Server};'
            'Server=YOUR_SQL_SERVER_NAME;'  
            'Database=UI_Project_DB;'
            'Trusted_Connection=yes;'
        )
        return conn
    except Exception as e:
        print("❌ Connection Error:", e)
        return None


# ----------------- BASIC INFO -----------------
def get_basic_info(cursor):
    """Fetch summary metrics from SQL Server database."""
    queries = {
        "Total Suppliers": "SELECT COUNT(*) FROM suppliers",
        "Total Products": "SELECT COUNT(*) FROM products",
        "Total Categories Dealing": "SELECT COUNT(DISTINCT category) FROM products",

        "Total Sale Value (Last 3 Months)": """
        SELECT ROUND(SUM(ABS(se.change_quantity) * p.price), 2)
        FROM stock_entries se
        JOIN products p ON p.product_id = se.product_id
        WHERE se.change_type = 'Sale'
        AND se.entry_date >= (
            SELECT DATEADD(MONTH, -3, MAX(entry_date))
            FROM stock_entries
        )
        """,

        "Total Restock Value (Last 3 Months)": """
        SELECT ROUND(SUM(se.change_quantity * p.price), 2)
        FROM stock_entries se
        JOIN products p ON p.product_id = se.product_id
        WHERE se.change_type = 'Restock'
        AND se.entry_date >= (
            SELECT DATEADD(MONTH, -3, MAX(entry_date))
            FROM stock_entries
        )
        """,

        "Below Reorder & No Pending Reorders": """
        SELECT COUNT(*)
        FROM products p
        WHERE p.stock_quantity < p.reorder_level
        AND p.product_id NOT IN (
            SELECT DISTINCT product_id FROM reorders WHERE status = 'Pending'
        )
        """
    }

    results = {}
    for label, query in queries.items():
        cursor.execute(query)
        value = cursor.fetchone()[0]
        results[label] = value

    return results


# ----------------- DETAILED TABLES -----------------
def get_additonal_tables(cursor):
    queries = {
        "Suppliers Contact Details": """
            SELECT supplier_name, contact_name, email, phone 
            FROM suppliers
        """,

        "Products with Supplier and Stock": """
            SELECT 
                p.product_name,
                s.supplier_name,
                p.stock_quantity,
                p.reorder_level
            FROM products p
            JOIN suppliers s ON p.supplier_id = s.supplier_id
            ORDER BY p.product_name ASC
        """,

        "Products Needing Reorder": """
            SELECT product_name, stock_quantity, reorder_level
            FROM products
            WHERE stock_quantity <= reorder_level
        """
    }

    tables = {}
    for label, query in queries.items():
        cursor.execute(query)
        rows = cursor.fetchall()
        col_names = [column[0] for column in cursor.description]
        table_data = [dict(zip(col_names, row)) for row in rows]
        tables[label] = table_data

    return tables


# ----------------- UTILITY FUNCTIONS -----------------
def get_categories(cursor):
    cursor.execute("SELECT DISTINCT category FROM products ORDER BY category ASC")
    return [row[0] for row in cursor.fetchall()]


def get_suppliers(cursor):
    cursor.execute("SELECT supplier_id, supplier_name FROM suppliers ORDER BY supplier_name ASC")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def add_new_manual_id(cursor, db, p_name, p_category, p_price, p_stock, p_reorder, p_supplier):
    query = "EXEC AddNewProductManualID ?, ?, ?, ?, ?, ?"
    cursor.execute(query, (p_name, p_category, p_price, p_stock, p_reorder, p_supplier))
    db.commit()


# ----------------- CHART DATA FUNCTIONS -----------------
def get_monthly_sales(cursor):
    cursor.execute("""
        SELECT FORMAT(entry_date, 'yyyy-MM') AS month,
               SUM(ABS(change_quantity * p.price)) AS total_sales
        FROM stock_entries se
        JOIN products p ON p.product_id = se.product_id
        WHERE change_type = 'Sale'
        GROUP BY FORMAT(entry_date, 'yyyy-MM')
        ORDER BY month
    """)
    rows = cursor.fetchall()
    return [{"month": row[0], "total_sales": float(row[1])} for row in rows]


def get_category_stock_distribution(cursor):
    cursor.execute("""
        SELECT category, SUM(stock_quantity) AS total_stock
        FROM products
        GROUP BY category
        ORDER BY total_stock DESC
    """)
    rows = cursor.fetchall()
    return [{"category": row[0], "total_stock": int(row[1])} for row in rows]


def get_all_products(cursor):
    cursor.execute("SELECT product_id, product_name FROM products ORDER BY product_name")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def get_product_history(cursor, product_id):
    query = "SELECT * FROM product_inventory_history WHERE product_id = ? ORDER BY record_date DESC"
    cursor.execute(query, (product_id,))
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def place_reorder(cursor, db, product_id, reorder_quantity):
    query = """
        INSERT INTO reorders (reorder_id, product_id, reorder_quantity, reorder_date, status)
        SELECT 
            ISNULL(MAX(reorder_id), 0) + 1,
            ?, ?, GETDATE(), 'Ordered'
        FROM reorders;
    """
    cursor.execute(query, (product_id, reorder_quantity))
    db.commit()


def get_pending_reorders(cursor):
    cursor.execute("""
        SELECT r.reorder_id, p.product_name
        FROM reorders r
        JOIN products p ON r.product_id = p.product_id
        WHERE r.status = 'Ordered'
    """)
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def mark_reorder_as_received(cursor, db, reorder_id):
    cursor.execute("EXEC MarkReorderAsReceived ?", (reorder_id,))
    db.commit()
