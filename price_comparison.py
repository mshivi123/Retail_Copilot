from serpapi.google_search import GoogleSearch
import numpy as np
import re
import requests
from bs4 import BeautifulSoup
import concurrent.futures
from functools import lru_cache

API_KEY = "12d66e4b460e6de17ea17c16a12fc48823c1ff27bba305013321eb973b3fb5d9"

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ---------------------------------------------------
# WORD MATCH SCORE
# ---------------------------------------------------
def match_score(product_words, title):
    if not title:
        return 0
    return len(product_words.intersection(title.lower().split()))


# ---------------------------------------------------
# FAST PRICE EXTRACTION
# ---------------------------------------------------
def extract_price(item):

    if item.get("extracted_price"):
        return float(item["extracted_price"])

    price_text = item.get("price")
    if price_text:
        nums = re.findall(r"\d+[,.]?\d*", price_text)
        if nums:
            return float(nums[0].replace(",", ""))

    return None


# ---------------------------------------------------
# CACHED GOOGLE SHOPPING
# ---------------------------------------------------
@lru_cache(maxsize=50)
def fetch_market_data(product):

    params = {
        "engine": "google_shopping",
        "q": product,
        "api_key": API_KEY,
        "gl": "in",
        "hl": "en"
    }

    return GoogleSearch(params).get_dict()


# ---------------------------------------------------
# FAST SCRAPER (COMMON)
# ---------------------------------------------------
def fetch_price(url, platform):

    try:
        res = requests.get(url, headers=HEADERS, timeout=2)

        soup = BeautifulSoup(res.text, "html.parser")

        if platform == "Amazon":
            tag = soup.find("span", {"class": "a-price-whole"})
        elif platform == "Flipkart":
            tag = soup.find("div", {"class": "_30jeq3"})
        else:
            return None

        if tag:
            nums = re.findall(r"\d+[,.]?\d*", tag.text)
            if nums:
                return float(nums[0].replace(",", ""))

    except:
        return None

    return None


# ---------------------------------------------------
# PARALLEL PLATFORM SEARCH
# ---------------------------------------------------
def force_platform_search(product):

    platforms = {
        "Amazon": "site:amazon.in",
        "Flipkart": "site:flipkart.com"
    }

    results_data = {}

    def search_one(name, query):

        params = {
            "engine": "google",
            "q": f"{product} {query}",
            "api_key": API_KEY,
            "gl": "in",
            "hl": "en"
        }

        data = GoogleSearch(params).get_dict()

        for item in data.get("organic_results", [])[:5]:

            link = item.get("link", "")

            if name.lower() not in link.lower():
                continue

            price = fetch_price(link, name)

            if price:
                return name, {
                    "price": price,
                    "title": item.get("title", ""),
                    "link": link,
                    "score": 1
                }

        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:

        futures = [
            executor.submit(search_one, name, query)
            for name, query in platforms.items()
        ]

        for f in concurrent.futures.as_completed(futures):
            result = f.result()
            if result:
                name, data = result
                results_data[name] = data

    return results_data


# ---------------------------------------------------
# EXTRACT BEST RESULTS
# ---------------------------------------------------
def extract_platform_prices(results, product_words):

    platform_data = {}

    for item in results.get("shopping_results", [])[:15]:

        source = item.get("source", "Unknown")
        title = item.get("title", "")
        link = item.get("product_link") or item.get("link") or "#"

        price = extract_price(item)
        if price is None:
            continue

        score = match_score(product_words, title)

        if source not in platform_data or score > platform_data[source]["score"]:
            platform_data[source] = {
                "price": price,
                "title": title,
                "link": link,
                "score": score
            }

    return platform_data


# ---------------------------------------------------
# REMOVE OUTLIERS
# ---------------------------------------------------
def remove_outliers(prices):

    arr = np.array(prices)

    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1

    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr

    filtered = [p for p in arr if low <= p <= high]
    outliers = [p for p in arr if p < low or p > high]

    return filtered, outliers


# ---------------------------------------------------
# PRICE MODEL
# ---------------------------------------------------
def calculate_price_bands(prices):

    arr = np.array(prices)

    median = np.median(arr)

    return {
        "lowest": round(arr.min(), 2),
        "highest": round(arr.max(), 2),
        "median": round(median, 2),
        "average_band": {
            "low": round(median * 0.95, 2),
            "high": round(median * 1.05, 2),
        },
        "recommended_band": {
            "low": round(median * 0.92, 2),
            "high": round(median * 0.98, 2),
        }
    }


# ---------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------
def compare_prices(product):

    product = product.lower().strip()
    product_words = set(product.split())

    results = fetch_market_data(product)

    platform_data = extract_platform_prices(results, product_words)

    # Skip heavy scraping if already found
    if not ("Amazon" in platform_data and "Flipkart" in platform_data):

        forced = force_platform_search(product)

        for k, v in forced.items():
            platform_data.setdefault(k, v)

    prices = [v["price"] for v in platform_data.values()]

    if not prices:
        return {"error": "No price data found"}

    filtered, outliers = remove_outliers(prices)

    if not filtered:
        return {"error": "Not enough valid prices"}

    summary = calculate_price_bands(filtered)

    return {
        "products": platform_data,
        "summary": summary,
        "sources": len(platform_data),
        "outliers": outliers
    }


# ---------------------------------------------------
# TEST
# ---------------------------------------------------
if __name__ == "__main__":

    result = compare_prices("iphone 15")

    from pprint import pprint
    pprint(result)