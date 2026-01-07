from flask import Flask, json, render_template, request, redirect, url_for,session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "112asdhdbabwyueoqwee"


DATABASE = "database.db"






conn = sqlite3.connect("database.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    image TEXT NOT NULL
)
""")



with open("orders.json", "r", encoding="utf-8") as f:
    menu_json = json.load(f)


menu_items = []
for category in menu_json:
    for item in category["items"]:
        menu_items.append(
            (item["name"], item["description"], item["price"], item["image"])
        )

c.executemany("""
INSERT INTO menu_items (name, description, price, image)
VALUES (?, ?, ?, ?)
""", menu_items)

conn.commit()
conn.close()
print("Menu items added successfully!")



def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn



@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            error = "Passwords do not match"
        else:
            try:
                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, password)
                )
                conn.commit()
                conn.close()
                return redirect(url_for('login'))  
            except sqlite3.IntegrityError:
                error = "Username already exists"

    return render_template("sign-up.html", error=error)


@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?", 
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"] 
            session["username"] = user["username"] 
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password"

    return render_template("log-in.html", error=error)

@app.route("/logout")
def logout():
    session.pop("user_id", None)  
    return redirect(url_for("login"))


# ------------------ OTHER PAGES ------------------

@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    user_id = session.get("user_id") 
    if not user_id:
        return redirect(url_for("login"))  

    item_ids = request.form.getlist("item_ids")  
    conn = get_db_connection()

    for item_id in item_ids:
        quantity = request.form.get(f"quantity_{item_id}", 1) 
        quantity = int(quantity)

        
        existing = conn.execute(
            "SELECT id, quantity FROM cart_items WHERE user_id = ? AND menu_item_id = ?",
            (user_id, item_id)
        ).fetchone()

        if existing:

            conn.execute(
                "UPDATE cart_items SET quantity = quantity + ? WHERE id = ?",
                (quantity, existing["id"])
            )
        else:
           
            conn.execute(
                "INSERT INTO cart_items (user_id, menu_item_id, quantity) VALUES (?, ?, ?)",
                (user_id, item_id, quantity)
            )

    conn.commit()
    conn.close()
    return redirect(url_for("cart"))


@app.route("/cart")
def cart():
    user_id = session.get("user_id") 
    if not user_id:
        return redirect(url_for("login")) 
    conn = get_db_connection()
    cart_items = conn.execute("""
        SELECT 
            cart_items.id,
            cart_items.quantity,
            menu_items.name,
            menu_items.description,
            menu_items.price,
            menu_items.image
        FROM cart_items
        JOIN menu_items ON cart_items.menu_item_id = menu_items.id
        WHERE cart_items.user_id = ?
    """, (user_id,)).fetchall()

    total = sum(item["price"] * item["quantity"] for item in cart_items)

    conn.close()

    return render_template("cart.html", cart_items=cart_items, total=total)



@app.route("/cart/delete/<int:cart_item_id>", methods=["POST"])
def delete_cart_item(cart_item_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM cart_items WHERE id = ?", (cart_item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("cart"))


@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/menu")
def menu():
    return render_template("menu.html")


@app.route("/account")
def account():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    conn = get_db_connection()

    user = conn.execute("""
        SELECT first_name, last_name, email, phone, gender, profile_image
        FROM users WHERE id = ?
    """, (user_id,)).fetchone()

    # Add full path for profile image
    if user['profile_image']:
        profile_image_url = url_for('static', filename=f"uploads/profile_images/{user['profile_image']}")
    else:
        profile_image_url = url_for('static', filename='images/default-profile.jpg')

    addresses = conn.execute("""
        SELECT id, label, address
        FROM addresses
        WHERE user_id = ?
    """, (user_id,)).fetchall()

    conn.close()

    return render_template("account.html", user=user, addresses=addresses, profile_image_url=profile_image_url)


@app.route("/receipt", methods=["POST"])
def receipt():
    # Get data from the form submission
    name = request.form["name"]
    gender = request.form["gender"]
    contact = request.form["contact"]
    zip_code = request.form["zip"]
    color = request.form["color"]
    time = request.form["time"]
    date = request.form["date"]
    quantity = request.form["quantity"]
    futureWeb = request.form["futureWeb"]

    # Pass data to the receipt template
    return render_template("receipt.html", name=name, gender=gender, contact=contact, zip=zip_code,
                           color=color, time=time, date=date, quantity=quantity, futureWeb=futureWeb)



@app.route("/checkout_receipt", methods=["POST", "GET"])
def checkout_receipt():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for('login')) 


    conn = get_db_connection()
    cart_items = conn.execute("""
        SELECT ci.id, ci.quantity, mi.name, mi.description, mi.price, mi.image
        FROM cart_items ci
        JOIN menu_items mi ON ci.menu_item_id = mi.id
        WHERE ci.user_id = ?
    """, (user_id,)).fetchall()

    
    total = sum(item['price'] * item['quantity'] for item in cart_items)

    return render_template("checkout_receipt.html", cart_items=cart_items, total=total)

@app.route('/checkout', methods=['POST'])
def checkout():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))  

    conn = get_db_connection()
    cart_items = conn.execute("""
        SELECT ci.id, ci.quantity, mi.name, mi.description, mi.price, mi.image
        FROM cart_items ci
        JOIN menu_items mi ON ci.menu_item_id = mi.id
        WHERE ci.user_id = ?
    """, (user_id,)).fetchall()

    total = sum(item['price'] * item['quantity'] for item in cart_items)

    

    
    conn.execute("""
        DELETE FROM cart_items WHERE user_id = ?
    """, (user_id,))
    conn.commit()


    return render_template("checkout_receipt.html", cart_items=cart_items, total=total)


@app.route("/update-profile", methods=["POST"])
def update_profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    email = request.form["email"]
    phone = request.form["phone"]
    gender = request.form["gender"]

    conn = get_db_connection()
    conn.execute("""
        UPDATE users
        SET first_name = ?, last_name = ?, email = ?, phone = ?, gender = ?
        WHERE id = ?
    """, (first_name, last_name, email, phone, gender, user_id))
    conn.commit()
    conn.close()

    return redirect(url_for("account"))


@app.route('/health-profile')
def health_profile():
    return render_template('health-profile.html')

@app.route('/nutrition-plan')
def nutrition_plan():
    return render_template('nutrition-plan.html')

@app.route('/order-history')
def order_history():
    return render_template('order-history.html')

@app.route('/apply')
def apply():
    return render_template('order-history.html')

@app.route("/add-address", methods=["POST"])
def add_address():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    label = request.form["label"]
    address = request.form["address"]

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO addresses (user_id, label, address)
        VALUES (?, ?, ?)
    """, (user_id, label, address))
    conn.commit()
    conn.close()

    return redirect(url_for("account"))
@app.route("/delete-address/<int:address_id>", methods=["POST"])
def delete_address(address_id):
    user_id = session.get("user_id")

    conn = get_db_connection()
    conn.execute("""
        DELETE FROM addresses
        WHERE id = ? AND user_id = ?
    """, (address_id, user_id))
    conn.commit()
    conn.close()

    return redirect(url_for("account"))


import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads/profile_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
import os
from werkzeug.utils import secure_filename

app.config['UPLOAD_FOLDER'] = 'static/uploads/profile_images'

@app.route("/update_profile_image", methods=["POST"])
def update_profile_image():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    file = request.files.get("profile_image")
    if file and file.filename:
        filename = secure_filename(f"user_{user_id}_{file.filename}")
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        conn = get_db_connection()
        # Save only the filename in DB
        conn.execute("UPDATE users SET profile_image = ? WHERE id = ?", (filename, user_id))
        conn.commit()
        conn.close()

    return redirect(url_for("account"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
