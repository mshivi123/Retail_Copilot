import matplotlib
matplotlib.use("Agg")

import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import os
import io

from sklearn.ensemble import RandomForestRegressor

os.makedirs("static", exist_ok=True)


def analyze_inventory(file):

    # ---------------- LOAD FILE (FINAL FIX)
    if hasattr(file, "filename"):

        filename = file.filename.lower()

        if filename.endswith(".xlsx"):
            file.seek(0)
            df = pd.read_excel(io.BytesIO(file.read()))
        else:
            file.seek(0)
            df = pd.read_csv(
                io.StringIO(file.read().decode("latin1")),
                on_bad_lines="skip"
            )

    else:
        df = pd.read_csv(file)

    # ---------------- CLEAN
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    required = ["product_name", "quantity_purchased", "cost_price", "mrp"]

    for col in required:
        if col not in df.columns:
            return {"error": f"Missing column: {col}"}

    # ---------------- SUMMARY
    ps = df.groupby("product_name").agg({
        "quantity_purchased": "sum",
        "cost_price": "mean",
        "mrp": "mean"
    }).reset_index()

    ps["inventory_value"] = ps["quantity_purchased"] * ps["cost_price"]
    ps = ps.sort_values("inventory_value", ascending=False)

    ps["cum_percent"] = ps["inventory_value"].cumsum() / ps["inventory_value"].sum()

    ps["abc_class"] = ps["cum_percent"].apply(
        lambda x: "A" if x <= 0.7 else "B" if x <= 0.9 else "C"
    )

    # ---------------- ML
    X = ps[["quantity_purchased", "cost_price"]]
    y = ps["mrp"]

    model = RandomForestRegressor(n_estimators=50, max_depth=5)
    model.fit(X, y)

    preds = model.predict(X)

    # ---------------- LOOP
    recs = []

    for i, row in enumerate(ps.itertuples()):

        demand = row.quantity_purchased

        recs.append({
            "product": row.product_name,
            "sales": int(demand),
            "abc": row.abc_class,
            "eoq": round(math.sqrt((2 * demand * 100) / 10), 2) if demand > 0 else 0,
            "reorder": round((demand / 30) * 7, 2) if demand > 0 else 0,
            "turnover": round(demand / (demand / 2 + 1), 2) if demand > 0 else 0,
            "forecast": round(preds[i], 2),
            "action": "Maintain"
        })

    # ---------------- CHARTS
    plt.bar(ps["product_name"], ps["quantity_purchased"])
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("static/sales_chart.png")
    plt.close()

    ps["abc_class"].value_counts().plot.pie(autopct="%1.0f%%")
    plt.savefig("static/abc_chart.png")
    plt.close()

    plt.plot(ps["product_name"], preds)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("static/forecast_chart.png")
    plt.close()

    return {
        "recommendations": recs,
        "total_products": len(ps),
        "sales_chart": "sales_chart.png",
        "abc_chart": "abc_chart.png",
        "forecast_chart": "forecast_chart.png"
    }
