import matplotlib
matplotlib.use("Agg")

import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import os

from sklearn.ensemble import RandomForestRegressor


# Ensure static folder exists (IMPORTANT for Render)
os.makedirs("static", exist_ok=True)


def analyze_inventory(file):

    # -----------------------------
    # LOAD FILE (FIXED)
    # -----------------------------
    if hasattr(file, "filename"):  # Flask upload
        filename = file.filename.lower()

        if filename.endswith(".xlsx"):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file, encoding="latin1", on_bad_lines="skip")

    else:  # Local testing
        if str(file).lower().endswith(".xlsx"):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file, encoding="latin1", on_bad_lines="skip")

    # Clean columns
    df.columns = df.columns.str.strip().str.lower()

    required_cols = [
        "product_name",
        "quantity_purchased",
        "cost_price",
        "mrp"
    ]

    for col in required_cols:
        if col not in df.columns:
            return {"error": f"Missing column: {col}"}

    # -----------------------------
    # PRODUCT SUMMARY
    # -----------------------------
    product_summary = df.groupby("product_name").agg({
        "quantity_purchased": "sum",
        "cost_price": "mean",
        "mrp": "mean"
    }).reset_index()

    # -----------------------------
    # ABC ANALYSIS
    # -----------------------------
    product_summary["inventory_value"] = (
        product_summary["quantity_purchased"] *
        product_summary["cost_price"]
    )

    product_summary = product_summary.sort_values(
        "inventory_value",
        ascending=False
    )

    total_value = product_summary["inventory_value"].sum()

    product_summary["cum_percent"] = (
        product_summary["inventory_value"].cumsum() / total_value
    )

    def classify(x):
        if x <= 0.7:
            return "A"
        elif x <= 0.9:
            return "B"
        else:
            return "C"

    product_summary["abc_class"] = product_summary["cum_percent"].apply(classify)

    avg_sales = product_summary["quantity_purchased"].mean()

    recommendations = []
    dead_stock = []
    insights = []

    # -----------------------------
    # ML MODEL (OPTIMIZED)
    # -----------------------------
    X = product_summary[["quantity_purchased", "cost_price"]]
    y = product_summary["mrp"]

    model = RandomForestRegressor(n_estimators=50, max_depth=5)
    model.fit(X, y)

    demand_predictions = model.predict(X)

    # -----------------------------
    # MAIN LOOP (FIXED INDEXING)
    # -----------------------------
    for idx, row in enumerate(product_summary.itertuples()):

        product = row.product_name
        sales = row.quantity_purchased
        cost = row.cost_price
        mrp = row.mrp

        margin = mrp - cost
        margin_percent = (margin / mrp) * 100 if mrp != 0 else 0

        # EOQ
        demand = sales
        eoq = math.sqrt((2 * demand * 100) / 10) if demand > 0 else 0

        # Reorder
        reorder = (demand / 30) * 7 if demand > 0 else 0

        # Turnover
        turnover = demand / (demand / 2 + 1) if demand > 0 else 0

        forecast = demand_predictions[idx]

        # Decision Logic
        if sales > avg_sales * 1.3:
            action = "Increase Stock"
            reason = "High demand product"

        elif sales < avg_sales * 0.3:
            dead_stock.append({
                "product": product,
                "sales": int(sales),
                "mrp": round(mrp, 2)
            })
            action = "Clear Stock"
            reason = "Very low demand"

        else:
            action = "Maintain Stock"
            reason = "Stable demand"

        if margin_percent < 10:
            insights.append(
                f"{product} has low profit margin ({margin_percent:.1f}%)."
            )

        recommendations.append({
            "product": product,
            "sales": int(sales),
            "abc": row.abc_class,
            "eoq": round(eoq, 2),
            "reorder": round(reorder, 2),
            "turnover": round(turnover, 2),
            "forecast": round(forecast, 2),
            "action": action
        })

    # -----------------------------
    # SALES CHART
    # -----------------------------
    plt.figure(figsize=(8, 5))
    plt.bar(product_summary["product_name"],
            product_summary["quantity_purchased"])
    plt.xticks(rotation=45)
    plt.title("Product Sales")
    plt.tight_layout()
    plt.savefig("static/sales_chart.png")
    plt.close()

    # -----------------------------
    # ABC CHART
    # -----------------------------
    abc_counts = product_summary["abc_class"].value_counts()

    plt.figure(figsize=(6, 6))
    plt.pie(
        abc_counts,
        labels=abc_counts.index,
        autopct="%1.0f%%"
    )
    plt.title("ABC Classification")
    plt.savefig("static/abc_chart.png")
    plt.close()

    # -----------------------------
    # FORECAST CHART
    # -----------------------------
    plt.figure(figsize=(8, 5))
    plt.plot(
        product_summary["product_name"],
        demand_predictions,
        marker="o"
    )
    plt.xticks(rotation=45)
    plt.title("Demand Forecast")
    plt.tight_layout()
    plt.savefig("static/forecast_chart.png")
    plt.close()

    # -----------------------------
    # FINAL OUTPUT
    # -----------------------------
    return {
        "recommendations": recommendations,
        "dead_stock": dead_stock,
        "insights": insights,
        "total_products": len(product_summary),
        "sales_chart": "sales_chart.png",
        "abc_chart": "abc_chart.png",
        "forecast_chart": "forecast_chart.png"
    }
