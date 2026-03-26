import requests
from bs4 import BeautifulSoup
import numpy as np


# ---------------------------------------------------
# FETCH MARKET INTEREST RATE
# ---------------------------------------------------

def fetch_interest_rates():

    url = "https://www.bankbazaar.com/business-loan-interest-rate.html"

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        page = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(page.content, "html.parser")
        text = soup.get_text()

        rates = []

        for word in text.split():
            if "%" in word:
                try:
                    val = float(word.replace("%", "").replace("p.a.", ""))
                    if 6 < val < 30:
                        rates.append(val)
                except:
                    pass

        if len(rates) > 0:
            return np.mean(rates)

        return 12.0

    except:
        return 12.0


# ---------------------------------------------------
# INDUSTRY BENCHMARK DATA
# ---------------------------------------------------

industry_de = {
    "retail": (0.5, 1.5),
    "manufacturing": (1.0, 2.0),
    "trading": (0.8, 1.8),
    "services": (0.3, 1.2),
    "restaurant": (0.7, 1.8),
    "ecommerce": (0.4, 1.6),
    "pharma": (0.6, 1.7),
    "textile": (1.0, 2.2),
    "electronics": (0.8, 1.9),
    "construction": (1.5, 3.0)
}


# ---------------------------------------------------
# MAIN ANALYZER FUNCTION
# ---------------------------------------------------

def analyze_loan(industry,
                          owner_capital,
                          existing_debt,
                          monthly_sales,
                          monthly_expenses,
                          inventory_value):

    interest_rate = fetch_interest_rates()

    monthly_profit = monthly_sales - monthly_expenses

    if monthly_profit <= 0:
        return {
            "error": "Business not profitable. Loan not recommended."
        }

    equity = owner_capital
    total_debt = existing_debt

    de_ratio = total_debt / equity

    # industry benchmark
    if industry in industry_de:
        min_de, max_de = industry_de[industry]
    else:
        min_de, max_de = (0.5, 1.5)

    # safe EMI
    safe_emi = 0.30 * monthly_profit

    monthly_rate = interest_rate / 100 / 12

    max_safe_loan = safe_emi / monthly_rate

    # industry constraint
    max_debt_allowed = max_de * equity
    extra_debt_allowed = max_debt_allowed - existing_debt

    extra_loan = min(max_safe_loan, extra_debt_allowed)

    if extra_loan < 0:
        extra_loan = 0

    recommended_de = (existing_debt + extra_loan) / equity

    return {

        "interest_rate": round(interest_rate,2),

        "monthly_profit": round(monthly_profit,2),

        "current_de_ratio": round(de_ratio,2),

        "industry_range": f"{min_de} - {max_de}",

        "safe_emi": round(safe_emi,2),

        "recommended_loan": round(extra_loan,2),

        "recommended_de": round(recommended_de,2)

    }