from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

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
        image_url TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_naam TEXT,
        mobile TEXT,
        thikana TEXT,
        product_naam TEXT,
        note TEXT,
        order_date TEXT
    )""")
    conn.commit()
    return conn

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
    products = [{"id":r[0],"naam":r[1],"category":r[2],"price":r[3],"image_url":r[4]} for r in rows]
    return render_template("index.html", products=products, categories=CATEGORIES, selected_cat=cat, success=success)

@app.route("/order", methods=["POST"])
def order():
    naam = request.form.get("naam", "")
    mobile = request.form.get("mobile", "")
    thikana = request.form.get("thikana", "")
    product_naam = request.form.get("product_naam", "")
    note = request.form.get("note", "")
    date = datetime.now().strftime("%d-%m-%Y %H:%M")
    conn = get_db()
    conn.execute("INSERT INTO orders (customer_naam,mobile,thikana,product_naam,note,order_date) VALUES (?,?,?,?,?,?)",
                 (naam, mobile, thikana, product_naam, note, date))
    conn.commit()
    conn.close()
    return redirect("/?success=1")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("username") == "mousumi" and request.form.get("password") == "admin123":
            session["admin"] = True
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
    products = [{"id":r[0],"naam":r[1],"category":r[2],"price":r[3],"image_url":r[4]} for r in rows]
    return render_template("admin_products.html", products=products, categories=CATEGORIES)

@app.route("/admin/add", methods=["GET", "POST"])
def admin_add():
    if not session.get("admin"):
        return redirect("/admin")
    if request.method == "POST":
        conn = get_db()
        conn.execute("INSERT INTO products (naam,category,price,image_url) VALUES (?,?,?,?)",
                     (request.form["naam"], request.form["category"],
                      int(request.form["price"]), request.form["image_url"]))
        conn.commit()
        conn.close()
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
    return redirect("/admin/products")

@app.route("/admin/orders")
def admin_orders():
    if not session.get("admin"):
        return redirect("/admin")
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    orders = [{"id":r[0],"naam":r[1],"mobile":r[2],"thikana":r[3],"product":r[4],"note":r[5],"date":r[6]} for r in rows]
    return render_template("admin_orders.html", orders=orders)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)