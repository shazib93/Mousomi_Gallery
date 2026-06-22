from flask import Flask, render_template, request, redirect, session, send_file, jsonify
import sqlite3
from datetime import datetime
import io
import json

app = Flask(__name__)
app.secret_key = "mousumi2026"

CATEGORIES = ["পোশাক", "গহনা", "কসমেটিক্স", "জুতা", "অন্যান্য"]

# ঢাকার জেলাগুলোর তালিকা
DHAKA_DISTRICTS = ["ঢাকা", "গাজীপুর", "নারায়ণগঞ্জ", "মানিকগঞ্জ", "মুন্সিগঞ্জ", "নরসিংদী", "কিশোরগঞ্জ", "টাঙ্গাইল"]

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
    conn.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_naam TEXT,
        mobile TEXT,
        district TEXT,
        thana TEXT,
        area TEXT,
        product_list TEXT,
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
    district = request.form.get("district", "")
    thana = request.form.get("thana", "")
    area = request.form.get("area", "")
    product_data = request.form.get("product_data", "[]")
    note = request.form.get("note", "")
    
    # ডেলিভারি চার্জ নির্ধারণ
    if district in DHAKA_DISTRICTS:
        delivery_charge = 80
    else:
        delivery_charge = 120
    
    # পণ্যের তালিকা পার্স করা
    try:
        products = json.loads(product_data)
    except:
        products = []
    
    # মোট দাম বের করা
    total = sum(p.get('price', 0) * p.get('qty', 1) for p in products) + delivery_charge
    
    # পণ্যের নামের তালিকা
    product_names = ", ".join([p.get('name', '') for p in products])
    
    # বিল নম্বর জেনারেশন
    bill_number = "MG-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    
    conn = get_db()
    conn.execute("""INSERT INTO orders 
        (customer_naam,mobile,district,thana,area,product_list,note,order_date,delivery_charge,total_price,bill_number) 
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                 (naam, mobile, district, thana, area, product_names, note, 
                  datetime.now().strftime("%d-%m-%Y %H:%M"), delivery_charge, total, bill_number))
    
    # স্টোক কমানো
    for p in products:
        conn.execute("UPDATE products SET stock = stock - ? WHERE naam=?", (p.get('qty', 1), p.get('name', '')))
    
    conn.commit()
    conn.close()
    
    log_activity("অর্ডার", f"{naam} - {product_names} - {total} টাকা")
    return redirect("/?success=1")

@app.route("/bill/<int:order_id>")
def generate_bill(order_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    if not row:
        return "অর্ডার পাওয়া যায়নি", 404
    
    bill_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>বিল - Mousomi's Gallery</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f8f4f0; padding: 30px; }}
            .bill-container {{ max-width: 600px; margin: 0 auto; background: #fff; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); padding: 40px; }}
            .header {{ text-align: center; border-bottom: 2px solid #d43f5a; padding-bottom: 20px; margin-bottom: 20px; }}
            .header h1 {{ color: #d43f5a; margin: 0; font-size: 2rem; }}
            .header p {{ color: #666; margin: 5px 0; }}
            .bill-details {{ margin: 20px 0; }}
            .bill-details table {{ width: 100%; border-collapse: collapse; }}
            .bill-details td {{ padding: 6px 0; }}
            .bill-details .label {{ color: #666; font-weight: 600; }}
            .items {{ margin: 20px 0; }}
            .items table {{ width: 100%; border-collapse: collapse; }}
            .items th {{ background: #d43f5a; color: #fff; padding: 10px; text-align: left; }}
            .items td {{ padding: 8px 10px; border-bottom: 1px solid #eee; }}
            .total {{ text-align: right; font-size: 1.2rem; font-weight: 700; color: #d43f5a; padding-top: 10px; border-top: 2px solid #d43f5a; margin-top: 10px; }}
            .footer {{ text-align: center; color: #999; font-size: 0.8rem; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px; }}
            .badge {{ display: inline-block; background: #25D366; color: #fff; padding: 2px 12px; border-radius: 20px; font-size: 0.7rem; }}
        </style>
    </head>
    <body>
        <div class="bill-container">
            <div class="header">
                <h1>🌸 Mousomi's Gallery</h1>
                <p>📍 মুগদা, ঢাকা-১২১৪ | 📞 ০১৬৭৩৯৬৩৮৫২</p>
                <p><span class="badge">বিল নম্বর: {row[10]}</span></p>
            </div>
            
            <div class="bill-details">
                <table>
                    <tr><td class="label">তারিখ</td><td>{row[7]}</td></tr>
                    <tr><td class="label">গ্রাহক</td><td>{row[1]}</td></tr>
                    <tr><td class="label">মোবাইল</td><td>{row[2]}</td></tr>
                    <tr><td class="label">জেলা</td><td>{row[3]}</td></tr>
                    <tr><td class="label">থানা</td><td>{row[4]}</td></tr>
                    <tr><td class="label">এলাকা</td><td>{row[5]}</td></tr>
                </table>
            </div>
            
            <div class="items">
                <h4>📦 পণ্যের তালিকা</h4>
                <table>
                    <tr><th>পণ্য</th><th align="right">দাম</th></tr>
                    {''.join([f"<tr><td>{item.strip()}</td><td align='right'>৳...</td></tr>" for item in row[6].split(',') if item.strip()])}
                </table>
            </div>
            
            <div class="total">
                <p>ডেলিভারি চার্জ: ৳{row[8]}</p>
                <p style="font-size:1.5rem;">মোট: ৳{row[9]}</p>
            </div>
            
            <div class="footer">
                <p>🙏 ধন্যবাদ! আপনার ব্যবসা আমাদের কাছে মূল্যবান।</p>
                <p>© ২০২৬ Mousomi's Gallery</p>
            </div>
        </div>
    </body>
    </html>
    """
    return bill_html

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
    orders = [{"id":r[0],"naam":r[1],"mobile":r[2],"district":r[3],"thana":r[4],"area":r[5],"product":r[6],"note":r[7],"date":r[8],"delivery":r[9],"total":r[10],"bill":r[11]} for r in rows]
    return render_template("admin_orders.html", orders=orders)

@app.route("/admin/report")
def admin_report():
    if not session.get("admin"):
        return redirect("/admin")
    conn = get_db()
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_sales = conn.execute("SELECT SUM(total_price) FROM orders").fetchone()[0] or 0
    logs = conn.execute("SELECT * FROM activity_log ORDER BY id DESC LIMIT 100").fetchall()
    cat_sales = conn.execute("""SELECT category, COUNT(orders.id) as count 
        FROM products LEFT JOIN orders ON products.naam = orders.product_list 
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