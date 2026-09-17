import requests, pandas as pd

BASE = "https://prices.runescape.wiki/api/v1/osrs"
HEADERS = {"User-Agent": "osrs-xp-cost-tracker - htpeyton@gmail.com"}
XP_99, MULT, BONES_PER_HR = 13_034_431, 3.5, 2550

def get(endpoint):
    data = requests.get(f"{BASE}/{endpoint}", headers=HEADERS, timeout=30).json()
    if endpoint == "mapping":
        return pd.DataFrame(data)
    t = pd.DataFrame.from_dict(data["data"], orient="index").rename_axis("id").reset_index()
    t["id"] = t["id"].astype(int)
    return t

xp = pd.read_csv("prayer_xp.csv")
df = (xp.merge(get("mapping")[["id", "name", "limit"]], on="name", how="left")
        .merge(get("latest")[["id", "high", "highTime"]], on="id", how="left")
        .merge(get("1h"), on="id", how="left"))

df["buy_price"] = df["avgHighPrice"].fillna(df["high"])
df["hourly_volume"] = df["highPriceVolume"].fillna(0) + df["lowPriceVolume"].fillna(0)
df["gp_per_xp"] = df["buy_price"] / df["xp"]
df["bones_to_99"] = XP_99 / (df["xp"] * MULT)
df["cost_to_99"] = df["bones_to_99"] * df["buy_price"]
df["hours_to_99"] = df["bones_to_99"] / BONES_PER_HR
df["days_buying"] = df["bones_to_99"] / df["limit"] * 4 / 24

now = pd.Timestamp.now(tz="UTC")
df["price_age_hrs"] = (now - pd.to_datetime(df["highTime"], unit="s", utc=True)).dt.total_seconds() / 3600

df = df.sort_values(["hours_to_99", "cost_to_99"])
df["on_frontier"] = df["cost_to_99"] < df["cost_to_99"].cummin().shift(fill_value=float("inf"))

keep = ["name", "xp", "buy_price", "gp_per_xp", "cost_to_99", "hours_to_99",
        "days_buying", "hourly_volume", "price_age_hrs", "limit", "on_frontier"]
df[keep].to_csv("prayer_cost_vs_time.csv", index=False)
print(df[keep].round(1).to_string(index=False))