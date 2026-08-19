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

# Monitoring starts at 6:00 AM Eastern.
# The watcher will not check websites between midnight and 6:00 AM.
MONITOR_START_HOUR = 6

# Stop monitoring after October 31, 2026.
END_DATE = datetime(
    2026,
    11,
    1,
    tzinfo=ZoneInfo(TIMEZONE)
)

# These are the ONLY phrases that trigger an alert.
# Matching is case-insensitive.
KEYWORDS = [
    "first anniversary",
    "1st anniversary",
]

# Seconds between website requests.
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


def find_keywords(text):
    """
    Return the anniversary phrases found on the page.

    Matching is case-insensitive.

    Only these phrases are considered:
        - first anniversary
        - 1st anniversary
    """

    text_lower = text.lower()

    return [
        keyword
        for keyword in KEYWORDS
        if keyword.lower() in text_lower
    ]


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
        print(
            "Watcher has reached its October 31, 2026 end date."
        )
        print("No websites will be checked.")
        return

    # ---------------------------------------------------------
    # Overnight pause.
    #
    # Do not check websites between midnight and 5:59 AM.
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

    # ---------------------------------------------------------
    # Check every website.
    # ---------------------------------------------------------

    for index, site in enumerate(sites):

        name = site.get("name", site["url"])
        url = site["url"]
        selector = site.get("selector", "")

        # Wait between requests.
        # Don't wait before the first website.
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
            print(
                f"Error fetching {name} ({url}): {e}"
            )
            continue

        # -----------------------------------------------------
        # Extract page text.
        #
        # IMPORTANT:
        # We do not save this text anywhere.
        # We only use it temporarily to search for the
        # specified phrases.
        # -----------------------------------------------------

        text = extract_text(
            response.text,
            selector
        )

        # Find our two specific phrases.
        matched_keywords = find_keywords(text)

        # True if either phrase was found.
        keyword_found = bool(matched_keywords)

        # -----------------------------------------------------
        # Retrieve previous state.
        # -----------------------------------------------------

        previous = state.get(url, {})

        previously_found = previous.get(
            "anniversary_found",
            False
        )

        # -----------------------------------------------------
        # Handle matches.
        # -----------------------------------------------------

        if keyword_found:

            found_any = True

            if not previously_found:

                print(
                    f"ANNIVERSARY PHRASE FOUND for {name}"
                )

                matched_text = ", ".join(
                    matched_keywords
                )

                send_discord(
                    webhook_url,
                    (
                        "\U0001F389 "
                        "**Anniversary announcement detected!**\n"
                        f"**{name}**\n"
                        f"{url}\n\n"
                        f"Matched: **{matched_text}**"
                    ),
                )

            else:

                print(
                    f"Anniversary phrase still present "
                    f"for {name}"
                )

        else:

            if previously_found:

                print(
                    f"Anniversary phrase no longer present "
                    f"for {name}"
                )

            else:

                print(
                    f"No matching anniversary phrase "
                    f"for {name}"
                )

        # -----------------------------------------------------
        # Save ONLY the information needed for future checks.
        #
        # We deliberately do NOT save:
        # - webpage text
        # - page contents
        # - private information
        # - diffs
        #
        # Only the site name and whether a matching phrase
        # was previously detected are stored.
        # -----------------------------------------------------

        state[url] = {
            "name": name,
            "anniversary_found": keyword_found,
        }

    # ---------------------------------------------------------
    # Save state.
    # ---------------------------------------------------------

    save_json(
        STATE_FILE,
        state
    )

    # ---------------------------------------------------------
    # Final status.
    # ---------------------------------------------------------

    if found_any:

        print(
            "Done — one or more sites contain "
            "a matching anniversary phrase."
        )

    else:

        print(
            "Done — no sites currently contain "
            "a matching anniversary phrase."
        )


if __name__ == "__main__":
    main()
