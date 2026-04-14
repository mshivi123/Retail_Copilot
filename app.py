from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash

from d_e_calculation import analyze_loan
from price_comparison import compare_prices
from stock_recommendation import analyze_inventory

os.makedirs("static", exist_ok=True)

app = Flask(__name__)
app.secret_key = "super_secret_key"


# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        email TEXT PRIMARY KEY,
        name TEXT,
        password TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()


init_db()


# ---------------- AUTH ----------------
def valid_password(p):
    return len(p) >= 6 and re.search(r"[A-Z]", p) and re.search(r"[0-9]", p)


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = email
            return redirect("/dashboard")

        flash("Invalid credentials", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not valid_password(password):
            flash("Weak password", "danger")
            return redirect("/register")

        conn = get_db()
        conn.execute(
            "INSERT OR IGNORE INTO users VALUES (?, ?, ?)",
            (email, name, generate_password_hash(password))
        )
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- INVENTORY ----------------
@app.route("/inventory", methods=["GET", "POST"])
def inventory():

    results = None
    error = None

    if request.method == "POST":

        file = request.files.get("file")

        if not file or file.filename == "":
            error = "Upload a file"

        else:
            try:
                results = analyze_inventory(file)
            except Exception as e:
                error = str(e)

    return render_template("inventory.html", results=results, error=error)


# ---------------- OTHER ----------------
@app.route("/price", methods=["GET", "POST"])
def price():
    result = None
    if request.method == "POST":
        result = compare_prices(request.form.get("product"))
    return render_template("price.html", result=result)


@app.route("/loan", methods=["GET", "POST"])
def loan():
    result = None
    if request.method == "POST":
        result = analyze_loan(
            request.form.get("industry").lower(),
            float(request.form.get("owner_capital")),
            float(request.form.get("existing_debt")),
            float(request.form.get("monthly_sales")),
            float(request.form.get("monthly_expenses")),
            float(request.form.get("inventory_value"))
        )
    return render_template("loan.html", result=result)


# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
