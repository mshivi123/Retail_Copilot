import matplotlib
matplotlib.use("Agg")

import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import os
import tempfile

from sklearn.ensemble import RandomForestRegressor

# Ensure static folder exists
os.makedirs("static", exist_ok=True)


def analyze_inventory(file):

    try:
        # ---------------- SAFE FILE LOAD ----------------
        filename = file.filename.lower()

        suffix = ".xlsx" if filename.endswith(".xlsx") else ".csv"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            temp_path = tmp.name

        if suffix == ".xlsx":
            df = pd.read_excel(temp_path)
        else:
            df = pd.read_csv(temp_path, encoding="latin1", on_bad_lines="skip")

        os.remove(temp_path)

    except Exception as e:
        return {"error": f"File read error: {str(e)}"}

    try:
        # ---------------- CLEAN COLUMNS ----------------
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        required_cols = [
            "product_name",
            "quantity_purchased",
            "cost_price",
            "mrp"
        ]

        for col in required_cols:
            if col not in df.columns:
                return {"error": f"Missing column: {col}"}

        # ---------------- SUMMARY ----------------
        ps = df.groupby("product_name").agg({
            "quantity_purchased": "sum",
            "cost_price": "mean",
            "mrp": "mean"
        }).reset_index()

        ps["inventory_value"] = ps["quantity_purchased"] * ps["cost_price"]

        ps = ps.sort_values("inventory_value", ascending=False)

        total_value = ps["inventory_value"].sum()

        if total_value == 0:
            return {"error": "Total inventory value is zero"}

        ps["cum_percent"] = ps["inventory_value"].cumsum() / total_value

        ps["abc_class"] = ps["cum_percent"].apply(
            lambda x: "A" if x <= 0.7 else "B" if x <= 0.9 else "C"
        )

        avg_sales = ps["quantity_purchased"].mean()

        # ---------------- ML MODEL ----------------
        X = ps[["quantity_purchased", "cost_price"]]
        y = ps["mrp"]

        model = RandomForestRegressor(n_estimators=50, max_depth=5)
        model.fit(X, y)

        preds = model.predict(X)

        # ---------------- LOOP ----------------
        recommendations = []
        dead_stock = []
        insights = []

        for i, row in enumerate(ps.itertuples()):

            product = row.product_name
            sales = row.quantity_purchased
            cost = row.cost_price
            mrp = row.mrp

            margin = mrp - cost
            margin_percent = (margin / mrp) * 100 if mrp != 0 else 0

            demand = sales

            eoq = math.sqrt((2 * demand * 100) / 10) if demand > 0 else 0
            reorder = (demand / 30) * 7 if demand > 0 else 0
            turnover = demand / (demand / 2 + 1) if demand > 0 else 0

            forecast = preds[i]

            if sales > avg_sales * 1.3:
                action = "Increase Stock"
            elif sales < avg_sales * 0.3:
                dead_stock.append({
                    "product": product,
                    "sales": int(sales),
                    "mrp": round(mrp, 2)
                })
                action = "Clear Stock"
            else:
                action = "Maintain Stock"

            if margin_percent < 10:
                insights.append(
                    f"{product} has low margin ({margin_percent:.1f}%)"
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

        # ---------------- CHARTS ----------------
        try:
            plt.figure()
            plt.bar(ps["product_name"], ps["quantity_purchased"])
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig("static/sales_chart.png")
            plt.close()

            plt.figure()
            ps["abc_class"].value_counts().plot.pie(autopct="%1.0f%%")
            plt.savefig("static/abc_chart.png")
            plt.close()

            plt.figure()
            plt.plot(ps["product_name"], preds, marker="o")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig("static/forecast_chart.png")
            plt.close()

        except Exception as e:
            return {"error": f"Chart error: {str(e)}"}

        # ---------------- FINAL OUTPUT ----------------
        return {
            "recommendations": recommendations,
            "dead_stock": dead_stock,
            "insights": insights,
            "total_products": len(ps),
            "sales_chart": "sales_chart.png",
            "abc_chart": "abc_chart.png",
            "forecast_chart": "forecast_chart.png"
        }

    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}
