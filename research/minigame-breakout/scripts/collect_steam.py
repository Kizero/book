"""Read-only public Steam review snapshot; reviews are not sales or retention."""
import concurrent.futures
import datetime
import json
import pathlib
import urllib.parse
import urllib.request

GAMES = {1942280: "Brotato", 1144910: "Space Gladiators", 1365010: "Lost Potato"}
ROOT = pathlib.Path(__file__).resolve().parents[1]

def fetch(item):
    appid, title = item
    params = dict(json=1, language="all", purchase_type="all", review_type="all",
                  filter="recent", num_per_page=1, cursor="*")
    url = f"https://store.steampowered.com/appreviews/{appid}?" + urllib.parse.urlencode(params)
    record = dict(appid=appid, title=title, url=url, query=params,
                  observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "PublicResearchSnapshot/1.0"})
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.load(response)
        record.update(success=data.get("success"), summary=data.get("query_summary"))
        if not data.get("success") or not data.get("query_summary"):
            record["error"] = "No usable review summary returned"
    except Exception as exc:
        record.update(success=False, error=str(exc))
    return record

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, GAMES.items()))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "evidence" / f"steam-{stamp}.json"
    output.write_text(json.dumps({"scope": "Public review summaries; default off-topic activity exclusion; no sales inference", "records": records}, ensure_ascii=False, indent=2) + "\n")
    print(output)
    for record in records:
        print(record["title"], json.dumps(record.get("summary") or record.get("error"), ensure_ascii=False))
