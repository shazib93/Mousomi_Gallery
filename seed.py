import sqlite3

def seed_database():
    conn = sqlite3.connect("mousumi.db")
    
    # টেবিল তৈরি
    conn.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        naam TEXT NOT NULL,
        category TEXT NOT NULL,
        price INTEGER NOT NULL,
        image_url TEXT NOT NULL,
        stock INTEGER DEFAULT 10,
        discount INTEGER DEFAULT 0
    )""")
    
    # ডেমো পণ্য (তোমার পণ্য দিয়ে Replace করো)
    products = [
        ("জামদানি শাড়ি", "পোশাক", 2000, "https://i.ibb.co/xxxxx/1.jpg", 10, 10),
        ("নেকলেস সেট", "গহনা", 850, "https://i.ibb.co/xxxxx/2.jpg", 15, 0),
        ("লিপস্টিক কম্বো", "কসমেটিক্স", 599, "https://i.ibb.co/xxxxx/3.jpg", 20, 15),
        ("লেদার স্যান্ডেল", "জুতা", 1800, "https://i.ibb.co/xxxxx/4.jpg", 8, 5),
    ]
    
    for p in products:
        conn.execute("INSERT INTO products (naam,category,price,image_url,stock,discount) VALUES (?,?,?,?,?,?)", p)
    
    conn.commit()
    conn.close()
    print("✅ ডেটাবেস তৈরি এবং ডেমো পণ্য যোগ করা হয়েছে!")

if __name__ == "__main__":
    seed_database()