import requests, pandas as pd
from io import StringIO

HEADERS = {"User-Agent": "osrs-xp-cost-tracker - htpeyton@gmail.com"}
params = {"action": "parse", "page": "Pay-to-play_Prayer_training",
          "prop": "text", "format": "json", "formatversion": 2}
html = requests.get("https://oldschool.runescape.wiki/api.php",
                    params=params, headers=HEADERS, timeout=30).json()["parse"]["text"]

tables = pd.read_html(StringIO(html))
t = next(t for t in tables if "Bury XP" in t.columns)
name_col = next(c for c in t.columns
                if str(c).startswith("Bones") and t[c].notna().any())

xp = t[[name_col, "Bury XP"]].rename(columns={name_col: "name", "Bury XP": "xp"})
xp.to_csv("prayer_xp.csv", index=False)
print(xp)