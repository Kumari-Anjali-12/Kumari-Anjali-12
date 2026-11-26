import json
import os
import urllib.request
from datetime import date, datetime, timedelta

TOKEN = os.environ["STATS_TOKEN"]
USER = os.environ["GH_USER"]


def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "streak-card",
        },
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]


now = datetime.utcnow()
today = now.date()

created = gql(
    "query($u:String!){user(login:$u){createdAt}}", {"u": USER}
)["user"]["createdAt"]
start_year = int(created[:4])

QUERY = """
query($u:String!,$from:DateTime!,$to:DateTime!){
  user(login:$u){
    contributionsCollection(from:$from,to:$to){
      contributionCalendar{
        weeks{contributionDays{date contributionCount}}
      }
    }
  }
}"""

counts = {}
for year in range(start_year, today.year + 1):
    frm = f"{year}-01-01T00:00:00Z"
    to = min(datetime(year, 12, 31, 23, 59, 59), now).strftime("%Y-%m-%dT%H:%M:%SZ")
    cal = gql(QUERY, {"u": USER, "from": frm, "to": to})["user"][
        "contributionsCollection"
    ]["contributionCalendar"]
    for week in cal["weeks"]:
        for day in week["contributionDays"]:
            d = date.fromisoformat(day["date"])
            if d <= today:
                counts[d] = day["contributionCount"]

total = sum(counts.values())
first_day = min(counts) if counts else today

# Current streak (if today has no contribution yet, start from yesterday)
d = today
if counts.get(d, 0) == 0:
    d -= timedelta(days=1)
cur_end = d
cur = 0
while counts.get(d, 0) > 0:
    cur += 1
    d -= timedelta(days=1)
cur_start = d + timedelta(days=1)

# Longest streak
best = run = 0
best_end = None
for d in sorted(counts):
    if counts[d] > 0:
        run += 1
        if run > best:
            best, best_end = run, d
    else:
        run = 0
best_start = best_end - timedelta(days=best - 1) if best_end else None


def fmt(d):
    return d.strftime("%b %d").replace(" 0", " ")


cur_range = f"{fmt(cur_start)} - {fmt(cur_end)}" if cur > 0 else "Start one today"
best_range = f"{fmt(best_start)} - {fmt(best_end)}" if best > 0 else "-"

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-label="GitHub contribution streak">
<rect width="495" height="195" rx="10" fill="#151515"/>
<g font-family="Segoe UI, Ubuntu, sans-serif" text-anchor="middle">
<line x1="165" y1="35" x2="165" y2="160" stroke="#444"/>
<line x1="330" y1="35" x2="330" y2="160" stroke="#444"/>
<text x="82" y="88" font-size="30" font-weight="700" fill="#ffffff">{total}</text>
<text x="82" y="118" font-size="14" fill="#ffffff">Total Contributions</text>
<text x="82" y="142" font-size="11" fill="#9e9e9e">{fmt(first_day)}, {first_day.year} - Present</text>
<circle cx="247" cy="70" r="40" fill="none" stroke="#ff9800" stroke-width="5"/>
<text x="247" y="81" font-size="30" font-weight="700" fill="#ffffff">{cur}</text>
<text x="247" y="132" font-size="14" font-weight="700" fill="#ff9800">Current Streak</text>
<text x="247" y="152" font-size="11" fill="#9e9e9e">{cur_range}</text>
<text x="412" y="88" font-size="30" font-weight="700" fill="#ffffff">{best}</text>
<text x="412" y="118" font-size="14" fill="#ffffff">Longest Streak</text>
<text x="412" y="142" font-size="11" fill="#9e9e9e">{best_range}</text>
</g>
</svg>
"""

os.makedirs("assets", exist_ok=True)
with open("assets/streak.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print("Streak card updated:", total, cur, best)
