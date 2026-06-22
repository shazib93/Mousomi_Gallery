from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
from datetime import datetime
import io

app = Flask(__name__)
app.secret_key = "mousumi2026"

CATEGORIES = ["পোশাক", "গহনা", "কসমেটিক্স", "জুতা", "অন্যান্য"]

def get_db():
    conn = sqlite3.connect("mousumi.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        naam TEXT NOT NULL,
        category TEXT NOT NULL,
        price INTEGER NOT NULL,
        image_url TEXT NOT NULL,
        stock INTEGER DEFAULT 10,
        discount INTEGER DEFAULT 0
    )""")
    # ... বাকি কোড
    # অর্ডার টেবিল – delivery_charge যোগ করা হলো
    conn.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_naam TEXT,
        mobile TEXT,
        thikana TEXT,
        product_naam TEXT,
        note TEXT,
        order_date TEXT,
        delivery_charge INTEGER DEFAULT 0,
        total_price INTEGER DEFAULT 0,
        bill_number TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        details TEXT,
        log_date TEXT
    )""")
    conn.commit()
    return conn

def log_activity(action, details):
    conn = get_db()
    conn.execute("INSERT INTO activity_log (action, details, log_date) VALUES (?,?,?)",
                 (action, details, datetime.now().strftime("%d-%m-%Y %H:%M")))
    conn.commit()
    conn.close()

@app.route("/")
def index():
    cat = request.args.get("cat", "")
    success = request.args.get("success", "")
    conn = get_db()
    cur = conn.cursor()
    if cat:
        cur.execute("SELECT * FROM products WHERE category=? ORDER BY id DESC", (cat,))
    else:
        cur.execute("SELECT * FROM products ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    products = [{"id":r[0],"naam":r[1],"category":r[2],"price":r[3],"image_url":r[4],"stock":r[5],"discount":r[6]} for r in rows]
    return render_template("index.html", products=products, categories=CATEGORIES, selected_cat=cat, success=success)

@app.route("/order", methods=["POST"])
def order():
    naam = request.form.get("naam", "")
    mobile = request.form.get("mobile", "")
    thikana = request.form.get("thikana", "")
    product_naam = request.form.get("product_naam", "")
    note = request.form.get("note", "")
    delivery_area = request.form.get("delivery_area", "ঢাকার ভেতরে")
    
    # ডেলিভারি চার্জ নির্ধারণ
    if delivery_area == "ঢাকার ভেতরে":
        delivery_charge = 80
    else:
        delivery_charge = 120
    
    # পণ্যের দাম বের করা
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT price FROM products WHERE naam=?", (product_naam,))
    row = cur.fetchone()
    product_price = row[0] if row else 0
    total = product_price + delivery_charge
    
    # বিল নম্বর জেনারেশন
    bill_number = "MG-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    
    conn.execute("INSERT INTO orders (customer_naam,mobile,thikana,product_naam,note,order_date,delivery_charge,total_price,bill_number) VALUES (?,?,?,?,?,?,?,?,?)",
                 (naam, mobile, thikana, product_naam, note, datetime.now().strftime("%d-%m-%Y %H:%M"), delivery_charge, total, bill_number))
    
    # স্টোক কমানো
    conn.execute("UPDATE products SET stock = stock - 1 WHERE naam=?", (product_naam,))
    conn.commit()
    conn.close()
    
    log_activity("অর্ডার", f"{naam} - {product_naam} - {total} টাকা")
    return redirect("/?success=1")

@app.route("/bill/<int:order_id>")
def generate_bill(order_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    if not row:
        return "অর্ডার পাওয়া যায়নি", 404
    
    bill = f"""
========================================
       Mousumi's Gallery
    📍 মুগদা, ঢাকা-১২১৪
    📞 ০১৬৭৩৯৬৩৮৫২
========================================
বিল নম্বর: {row[7]}
তারিখ: {row[6]}
----------------------------------------
গ্রাহক: {row[1]}
মোবাইল: {row[2]}
ঠিকানা: {row[3]}
----------------------------------------
পণ্য: {row[4]}
মূল্য: {row[5]} টাকা
ডেলিভারি চার্জ: {row[7]} টাকা
----------------------------------------
মোট: {row[8]} টাকা
========================================
        ধন্যবাদ! শুভ দিন। 😊
========================================
"""
    return send_file(io.BytesIO(bill.encode('utf-8')), mimetype='text/plain', as_attachment=True, download_name=f"bill_{row[7]}.txt")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("username") == "mousumi" and request.form.get("password") == "admin123":
            session["admin"] = True
            log_activity("লগইন", "অ্যাডমিন লগইন")
            return redirect("/admin/products")
        return render_template("admin_login.html", error=True)
    if session.get("admin"):
        return redirect("/admin/products")
    return render_template("admin_login.html", error=False)

@app.route("/admin/products")
def admin_products():
    if not session.get("admin"):
        return redirect("/admin")
    conn = get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY category, id DESC").fetchall()
    conn.close()
    products = [{"id":r[0],"naam":r[1],"category":r[2],"price":r[3],"image_url":r[4],"stock":r[5],"discount":r[6]} for r in rows]
    return render_template("admin_products.html", products=products, categories=CATEGORIES)

@app.route("/admin/add", methods=["GET", "POST"])
def admin_add():
    if not session.get("admin"):
        return redirect("/admin")
    if request.method == "POST":
        conn = get_db()
        conn.execute("INSERT INTO products (naam,category,price,image_url,stock,discount) VALUES (?,?,?,?,?,?)",
                     (request.form["naam"], request.form["category"],
                      int(request.form["price"]), request.form["image_url"],
                      int(request.form.get("stock", 10)), int(request.form.get("discount", 0))))
        conn.commit()
        conn.close()
        log_activity("পণ্য যোগ", f"{request.form['naam']} - {request.form['category']}")
        return redirect("/admin/products")
    return render_template("admin_add.html", categories=CATEGORIES)

@app.route("/admin/delete/<int:id>")
def admin_delete(id):
    if not session.get("admin"):
        return redirect("/admin")
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()
    log_activity("পণ্য ডিলিট", f"ID: {id}")
    return redirect("/admin/products")

@app.route("/admin/orders")
def admin_orders():
    if not session.get("admin"):
        return redirect("/admin")
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    orders = [{"id":r[0],"naam":r[1],"mobile":r[2],"thikana":r[3],"product":r[4],"note":r[5],"date":r[6],"delivery":r[7],"total":r[8],"bill":r[9]} for r in rows]
    return render_template("admin_orders.html", orders=orders)

@app.route("/admin/report")
def admin_report():
    if not session.get("admin"):
        return redirect("/admin")
    conn = get_db()
    # মোট অর্ডার
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    # মোট বিক্রি
    total_sales = conn.execute("SELECT SUM(total_price) FROM orders").fetchone()[0] or 0
    # সব অ্যাক্টিভিটি
    logs = conn.execute("SELECT * FROM activity_log ORDER BY id DESC LIMIT 100").fetchall()
    # ক্যাটাগরি ভিত্তিক বিক্রি
    cat_sales = conn.execute("""SELECT category, COUNT(orders.id) as count 
        FROM products LEFT JOIN orders ON products.naam = orders.product_naam 
        GROUP BY category""").fetchall()
    conn.close()
    return render_template("admin_report.html", 
                         total_orders=total_orders, 
                         total_sales=total_sales,
                         logs=logs,
                         cat_sales=cat_sales)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    log_activity("লগআউট", "অ্যাডমিন লগআউট")
    return redirect("/admin")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)