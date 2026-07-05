from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB = "inventory.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT "General",
            sku TEXT UNIQUE,
            quantity INTEGER DEFAULT 0,
            min_stock INTEGER DEFAULT 5,
            unit TEXT DEFAULT "units",
            price REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            note TEXT DEFAULT "",
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )''')
        # Sample data
        existing = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        if existing == 0:
            samples = [
                ('Steel Rods', 'Raw Material', 'SKU001', 150, 20, 'kg', 45.0),
                ('Aluminium Sheets', 'Raw Material', 'SKU002', 80, 15, 'sheets', 120.0),
                ('Bearings 6205', 'Components', 'SKU003', 45, 10, 'pcs', 85.0),
                ('Bolts M10', 'Fasteners', 'SKU004', 500, 100, 'pcs', 2.5),
                ('Hydraulic Oil', 'Consumables', 'SKU005', 8, 10, 'liters', 350.0),
                ('Safety Gloves', 'Safety', 'SKU006', 30, 20, 'pairs', 25.0),
            ]
            for s in samples:
                conn.execute(
                    'INSERT INTO products (name,category,sku,quantity,min_stock,unit,price) VALUES (?,?,?,?,?,?,?)', s
                )
        conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    with get_db() as conn:
        query = 'SELECT * FROM products WHERE 1=1'
        params = []
        if search:
            query += ' AND (name LIKE ? OR sku LIKE ?)'
            params += [f'%{search}%', f'%{search}%']
        if category:
            query += ' AND category = ?'
            params.append(category)
        query += ' ORDER BY name'
        products = conn.execute(query, params).fetchall()
        return jsonify([dict(p) for p in products])

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json()
    name = data.get('name','').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    sku = data.get('sku') or f"SKU{datetime.now().strftime('%H%M%S')}"
    with get_db() as conn:
        try:
            cursor = conn.execute(
                'INSERT INTO products (name,category,sku,quantity,min_stock,unit,price) VALUES (?,?,?,?,?,?,?)',
                (name, data.get('category','General'), sku,
                 int(data.get('quantity',0)), int(data.get('min_stock',5)),
                 data.get('unit','units'), float(data.get('price',0)))
            )
            conn.commit()
            p = conn.execute('SELECT * FROM products WHERE id=?', (cursor.lastrowid,)).fetchone()
            return jsonify(dict(p)), 201
        except sqlite3.IntegrityError:
            return jsonify({'error': 'SKU already exists'}), 400

@app.route('/api/products/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    with get_db() as conn:
        conn.execute('DELETE FROM transactions WHERE product_id=?', (pid,))
        conn.execute('DELETE FROM products WHERE id=?', (pid,))
        conn.commit()
        return jsonify({'success': True})

@app.route('/api/transaction', methods=['POST'])
def add_transaction():
    data = request.get_json()
    pid = data.get('product_id')
    ttype = data.get('type')
    qty = int(data.get('quantity', 0))
    note = data.get('note', '')

    if not pid or not ttype or qty <= 0:
        return jsonify({'error': 'Invalid data'}), 400

    with get_db() as conn:
        product = conn.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        if not product:
            return jsonify({'error': 'Product not found'}), 404

        new_qty = product['quantity'] + qty if ttype == 'in' else product['quantity'] - qty
        if new_qty < 0:
            return jsonify({'error': 'Insufficient stock'}), 400

        conn.execute('UPDATE products SET quantity=? WHERE id=?', (new_qty, pid))
        conn.execute(
            'INSERT INTO transactions (product_id,type,quantity,note) VALUES (?,?,?,?)',
            (pid, ttype, qty, note)
        )
        conn.commit()
        p = conn.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        return jsonify(dict(p))

@app.route('/api/transactions')
def get_transactions():
    with get_db() as conn:
        rows = conn.execute('''
            SELECT t.*, p.name as product_name, p.unit
            FROM transactions t
            JOIN products p ON t.product_id = p.id
            ORDER BY t.created_at DESC LIMIT 50
        ''').fetchall()
        return jsonify([dict(r) for r in rows])

@app.route('/api/stats')
def get_stats():
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        low = conn.execute('SELECT COUNT(*) FROM products WHERE quantity <= min_stock').fetchone()[0]
        out = conn.execute('SELECT COUNT(*) FROM products WHERE quantity = 0').fetchone()[0]
        value = conn.execute('SELECT COALESCE(SUM(quantity*price),0) FROM products').fetchone()[0]
        categories = conn.execute('SELECT DISTINCT category FROM products').fetchall()
        return jsonify({
            'total': total, 'low_stock': low,
            'out_of_stock': out, 'total_value': round(value, 2),
            'categories': [r['category'] for r in categories]
        })

if __name__ == '__main__':
    init_db()
    print("\n🚀 Inventory System running at http://localhost:5000\n")
    app.run(debug=True)