import json
import hashlib
import os
import requests
from bs4 import BeautifulSoup

STATE_FILE = "data/state.json"
SITES_FILE = "sites.json"


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def extract_text(html, selector):
    soup = BeautifulSoup(html, "html.parser")
    if selector:
        node = soup.select_one(selector)
        text = node.get_text(" ", strip=True) if node else soup.get_text(" ", strip=True)
    else:
        text = soup.get_text(" ", strip=True)
    return " ".join(text.split())


def send_discord(webhook_url, message):
    if not webhook_url:
        print("No webhook configured, skipping notification.")
        return
    try:
        requests.post(webhook_url, json={"content": message}, timeout=15)
    except Exception as e:
        print(f"Failed to send Discord notification: {e}")


def main():
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    sites = load_json(SITES_FILE, [])
    state = load_json(STATE_FILE, {})

    if not sites:
        print("No sites configured in sites.json")
        return

    changed_any = False

    for site in sites:
        name = site.get("name", site["url"])
        url = site["url"]
        selector = site.get("selector")

        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; GundamEventWatcher/1.0)"},
                timeout=20,
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"Error fetching {name} ({url}): {e}")
            continue

        text = extract_text(resp.text, selector)
        new_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        prev_entry = state.get(url)

        if prev_entry is None:
            # First time seeing this site: record the baseline, don't alert yet.
            print(f"Baseline recorded for {name}")
        elif prev_entry["hash"] != new_hash:
            print(f"Change detected for {name}")
            send_discord(
                webhook_url,
                f"\U0001F4E2 **{name}** just updated their events page!\n{url}",
            )
            changed_any = True
        else:
            print(f"No change for {name}")

        state[url] = {"hash": new_hash, "name": name}

    save_json(STATE_FILE, state)
    print("Done — changes detected." if changed_any else "Done — no changes.")


if __name__ == "__main__":
    main()
