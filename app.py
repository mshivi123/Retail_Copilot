from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash

from d_e_calculation import analyze_loan
from price_comparison import compare_prices
from stock_recommendation import analyze_inventory
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

app = Flask(__name__)
app.secret_key = "super_secret_key"


# -------------------
# CREATE UPLOAD FOLDER
# -------------------

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# -------------------
# DATABASE
# -------------------

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


# -------------------
# PASSWORD VALIDATION
# -------------------

def valid_password(p):

    return (
        len(p) >= 6 and
        re.search(r"[A-Z]", p) and
        re.search(r"[0-9]", p)
    )


# -------------------
# LOGIN
# -------------------

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

        conn.close()

        if user:

            if check_password_hash(user["password"], password):

                session["user"] = email

                return redirect("/dashboard")

            else:
                flash("Incorrect password", "danger")

        else:

            flash("User not found. Please register.", "warning")

            return redirect("/register")

    return render_template("login.html")


# -------------------
# REGISTER
# -------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        try:

            name = request.form.get("name")
            email = request.form.get("email")
            password = request.form.get("password")

            if len(name) < 2:

                flash("Name too short", "danger")

                return redirect("/register")

            if not valid_password(password):

                flash(
                    "Password must be 6+ chars, include 1 uppercase & 1 number",
                    "danger"
                )

                return redirect("/register")

            conn = get_db()

            existing = conn.execute(
                "SELECT * FROM users WHERE email=?",
                (email,)
            ).fetchone()

            if existing:

                conn.close()

                flash("User already exists. Please login.", "warning")

                return redirect("/")

            conn.execute(
                "INSERT INTO users (email, name, password) VALUES (?, ?, ?)",
                (email, name, generate_password_hash(password))
            )

            conn.commit()
            conn.close()

            flash("Registered successfully! Please login.", "success")

            return redirect("/")

        except Exception as e:

            print("ERROR:", e)

            flash("Something went wrong. Try again.", "danger")

            return redirect("/register")

    return render_template("register.html")


# -------------------
# DASHBOARD
# -------------------

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    return render_template("dashboard.html", user=session["user"])


# -------------------
# LOGOUT
# -------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# -------------------
# LOAN ANALYZER
# -------------------

@app.route("/loan", methods=["GET", "POST"])
def loan():

    result = None

    if request.method == "POST":

        industry = request.form.get("industry").lower()

        owner_capital = float(request.form.get("owner_capital"))
        existing_debt = float(request.form.get("existing_debt"))
        monthly_sales = float(request.form.get("monthly_sales"))
        monthly_expenses = float(request.form.get("monthly_expenses"))
        inventory_value = float(request.form.get("inventory_value"))

        result = analyze_loan(
            industry,
            owner_capital,
            existing_debt,
            monthly_sales,
            monthly_expenses,
            inventory_value
        )

    return render_template("loan.html", result=result)


# -------------------
# INVENTORY ANALYSIS
# -------------------

@app.route("/inventory", methods=["GET", "POST"])
def inventory():

    results = None
    error = None

    if request.method == "POST":

        file = request.files.get("file")

        if not file:

            error = "Please upload a dataset"

        else:

            filepath = os.path.join(UPLOAD_FOLDER, file.filename)

            file.save(filepath)

            try:

                results = analyze_inventory(filepath)

            except Exception as e:

                error = str(e)

    return render_template(
        "inventory.html",
        results=results,
        error=error
    )


# -------------------
# PRICE COMPARISON
# -------------------

@app.route("/price", methods=["GET", "POST"])
def price():

    result = None

    if request.method == "POST":

        product = request.form.get("product")

        result = compare_prices(product)

    return render_template("price.html", result=result)


# -------------------
# RUN APP
# -------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)