#!/usr/bin/env python3
"""SAM.gov Opportunities Scraper - pulls active solicitations from the last 7 days."""

import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

API_KEY = os.environ.get("SAM_API_KEY", "SAM-c4fabfb2-fcf1-4225-a9c5-b56c6b9e91bd")
BASE_URL = "https://api.sam.gov/opportunities/v2/search"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_page(posted_from, posted_to, offset=0, limit=100):
    params = urllib.parse.urlencode({
        "api_key": API_KEY,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "limit": limit,
        "offset": offset,
        "ptype": "o",
        "status": "active",
    })
    url = f"{BASE_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "UncleSamsScraper/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def extract(o):
    path = (o.get("fullParentPathName") or "").split(".")
    contacts = []
    for p in o.get("pointOfContact") or []:
        contacts.append({"name": p.get("fullName",""), "email": p.get("email",""), "phone": p.get("phone","")})
    return {
        "noticeId": o.get("noticeId",""),
        "title": o.get("title",""),
        "solicitationNumber": o.get("solicitationNumber",""),
        "agency": path[1] if len(path) > 1 else "",
        "office": path[-1] if path else "",
        "postedDate": o.get("postedDate",""),
        "responseDeadline": o.get("responseDeadLine",""),
        "type": o.get("type",""),
        "naicsCode": o.get("naicsCode",""),
        "naicsDescription": "",
        "setAside": o.get("typeOfSetAsideDescription") or "",
        "active": o.get("active",""),
        "contacts": contacts,
        "uiLink": o.get("uiLink",""),
        "placeOfPerformance": o.get("placeOfPerformance",{}),
    }


def main():
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    fmt = "%m/%d/%Y"
    posted_from, posted_to = week_ago.strftime(fmt), today.strftime(fmt)

    print(f"SAM.gov Scraper | {posted_from} to {posted_to}")

    all_opps = []
    offset = 0
    while True:
        print(f"  Fetching offset {offset}...")
        try:
            data = fetch_page(posted_from, posted_to, offset)
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  HTTP {e.code}: {body[:200]}")
            break
        except Exception as e:
            print(f"  Error: {e}")
            break

        total = data.get("totalRecords", 0)
        batch = data.get("opportunitiesData", [])
        all_opps.extend(extract(o) for o in batch)
        print(f"  Got {len(batch)} (total: {total}, fetched: {len(all_opps)})")

        if len(all_opps) >= total or not batch:
            break
        offset += 100

    opportunities = all_opps

    # Save JSON
    os.makedirs(f"{SCRIPT_DIR}/data", exist_ok=True)
    with open(f"{SCRIPT_DIR}/data/opportunities.json", "w") as f:
        json.dump(opportunities, f, indent=2)

    digest = opportunities[:5]
    with open(f"{SCRIPT_DIR}/data/digest.json", "w") as f:
        json.dump(digest, f, indent=2)

    # Generate data.js
    last_updated = today.strftime("%B %d, %Y at %I:%M %p %Z")
    with open(f"{SCRIPT_DIR}/data.js", "w") as f:
        f.write(f"const LAST_UPDATED = {json.dumps(last_updated)};\n\n")
        f.write(f"const OPPORTUNITIES = {json.dumps(opportunities, indent=2)};\n\n")
        f.write(f"const DIGEST = {json.dumps(digest, indent=2)};\n")

    print(f"\nDone: {len(opportunities)} opportunities saved")


if __name__ == "__main__":
    main()
