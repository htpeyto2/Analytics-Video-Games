import requests, pandas as pd
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"  # read/write data/ from any cwd
BASE = "https://prices.runescape.wiki/api/v1/osrs"
HEADERS = {"User-Agent": "osrs-xp-cost-tracker - htpeyton@gmail.com"}
XP_99, MULT, BONES_PER_HR = 13_034_431, 3.5, 2550
MAX_AGE_HRS = 6  # prices older than this are too stale to trust for the frontier

# GE buy limits are per 4-hour window, timed from the first item bought in that
# window (so days_buying below is "windows needed" x 4h, expressed in days).
# A few items have no limit published anywhere: the GE page shows "-" and the
# wiki's master list still prompts editors to add one, i.e. nobody has worked it
# out yet. That's *unknown*, not unlimited, so we leave it blank and flag the row
# rather than invent a number that would silently skew days_buying. Don't expect
# these to fill in on their own - check limit_known before trusting days_buying.
LIMIT_OVERRIDES = {}  # name -> limit, for any value confirmed off-wiki

def get(endpoint):
    data = requests.get(f"{BASE}/{endpoint}", headers=HEADERS, timeout=30).json()
    if endpoint == "mapping":
        return pd.DataFrame(data)
    t = pd.DataFrame.from_dict(data["data"], orient="index").rename_axis("id").reset_index()
    t["id"] = t["id"].astype(int)
    return t

xp = pd.read_csv(DATA / "prayer_xp.csv")
df = (xp.merge(get("mapping")[["id", "name", "limit"]], on="name", how="left")
        .merge(get("latest")[["id", "high", "highTime"]], on="id", how="left")
        .merge(get("1h"), on="id", how="left"))

df["limit"] = df["limit"].fillna(df["name"].map(LIMIT_OVERRIDES))
df["limit_known"] = df["limit"].notna() & (df["limit"] > 0)

df["buy_price"] = df["avgHighPrice"].fillna(df["high"])
df["hourly_volume"] = df["highPriceVolume"].fillna(0) + df["lowPriceVolume"].fillna(0)
df["gp_per_xp"] = df["buy_price"] / df["xp"]
df["bones_to_99"] = XP_99 / (df["xp"] * MULT)
df["cost_to_99"] = df["bones_to_99"] * df["buy_price"]
df["hours_to_99"] = df["bones_to_99"] / BONES_PER_HR
# windows needed x 4h per window / 24h per day; blank where the limit is unknown
df["days_buying"] = df["bones_to_99"] / df["limit"].where(df["limit_known"]) * 4 / 24

now = pd.Timestamp.now(tz="UTC")
df["price_age_hrs"] = (now - pd.to_datetime(df["highTime"], unit="s", utc=True)).dt.total_seconds() / 3600

df["reliable"] = (df["hourly_volume"] > 0) & (df["price_age_hrs"] <= MAX_AGE_HRS)

df = df.sort_values(["hours_to_99", "cost_to_99"])
rel = df[df["reliable"]]
is_front = rel["cost_to_99"] < rel["cost_to_99"].cummin().shift(fill_value=float("inf"))
df["on_frontier"] = df.index.isin(rel.index[is_front])

keep = ["name", "xp", "buy_price", "gp_per_xp", "cost_to_99", "hours_to_99",
        "days_buying", "hourly_volume", "price_age_hrs", "limit", "limit_known",
        "reliable", "on_frontier"]
df[keep].to_csv(DATA / "prayer_cost_vs_time.csv", index=False)
print(df[keep].round(1).to_string(index=False))