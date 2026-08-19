import json
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


STATE_FILE = "data/state.json"
SITES_FILE = "sites.json"

# Eastern Time
TIMEZONE = "America/Toronto"

# Don't check websites between midnight and 6:00 AM Eastern.
MONITOR_START_HOUR = 6

# Stop the project after October 31, 2026.
END_DATE = datetime(2026, 11, 1, tzinfo=ZoneInfo(TIMEZONE))

# Word we're looking for.
KEYWORD = "anniversary"

# Seconds to wait between website requests.
REQUEST_DELAY = 2


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

        if node:
            text = node.get_text(" ", strip=True)
        else:
            text = soup.get_text(" ", strip=True)
    else:
        text = soup.get_text(" ", strip=True)

    return " ".join(text.split())


def contains_keyword(text):
    return KEYWORD.lower() in text.lower()


def send_discord(webhook_url, message):
    if not webhook_url:
        print("No webhook configured, skipping notification.")
        return

    try:
        response = requests.post(
            webhook_url,
            json={"content": message},
            timeout=15,
        )

        if response.status_code >= 400:
            print(
                f"Discord webhook returned HTTP "
                f"{response.status_code}: {response.text}"
            )

    except Exception as e:
        print(f"Failed to send Discord notification: {e}")


def main():
    now = datetime.now(ZoneInfo(TIMEZONE))

    print(
        "Current Eastern time: "
        f"{now.strftime('%Y-%m-%d %I:%M:%S %p %Z')}"
    )

    # ---------------------------------------------------------
    # Stop completely after October 31, 2026.
    # ---------------------------------------------------------
    if now >= END_DATE:
        print("Watcher has reached its October 31, 2026 end date.")
        print("No websites will be checked.")
        return

    # ---------------------------------------------------------
    # Overnight pause: midnight through 5:59 AM Eastern.
    # ---------------------------------------------------------
    if now.hour < MONITOR_START_HOUR:
        print(
            "Outside monitoring hours. "
            "Monitoring resumes at 6:00 AM Eastern."
        )
        return

    print("Within monitoring hours.")

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    sites = load_json(SITES_FILE, [])
    state = load_json(STATE_FILE, {})

    if not sites:
        print("No sites configured in sites.json")
        return

    found_any = False

    for index, site in enumerate(sites):
        name = site.get("name", site["url"])
        url = site["url"]
        selector = site.get("selector", "")

        # Wait between requests, but not before the first one.
        if index > 0:
            time.sleep(REQUEST_DELAY)

        try:
            print(f"Checking {name}...")

            response = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(compatible; GundamEventWatcher/1.0)"
                    )
                },
                timeout=20,
            )

            response.raise_for_status()

        except Exception as e:
            print(f"Error fetching {name} ({url}): {e}")
            continue

        text = extract_text(response.text, selector)

        keyword_found = contains_keyword(text)

        previous = state.get(url, {})

        # What was the keyword status during the previous check?
        previously_found = previous.get("anniversary_found", False)

        if keyword_found:
            found_any = True

            if not previously_found:
                # The word has appeared since the previous check.
                print(f"ANNIVERSARY FOUND for {name}")

                send_discord(
                    webhook_url,
                    (
                        f"\U0001F389 **Anniversary keyword detected!**\n"
                        f"**{name}**\n"
                        f"{url}\n\n"
                        f"The page now contains the word "
                        f"**{KEYWORD}**."
                    ),
                )

            else:
                print(f"Anniversary still present for {name}")

        else:
            if previously_found:
                print(f"Anniversary no longer present for {name}")
            else:
                print(f"No anniversary keyword for {name}")

        # Only save the information we actually need.
        #
        # We deliberately DO NOT save the webpage text.
        # This keeps private/unrelated page content out of state.json.
        state[url] = {
            "name": name,
            "anniversary_found": keyword_found,
        }

    save_json(STATE_FILE, state)

    if found_any:
        print("Done — one or more sites contain the anniversary keyword.")
    else:
        print("Done — no sites currently contain the anniversary keyword.")


if __name__ == "__main__":
    main()
