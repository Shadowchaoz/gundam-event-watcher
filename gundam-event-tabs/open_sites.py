import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


SITES_FILE = Path("sites.json")


def load_sites():
    with open(SITES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    sites = load_sites()

    if not sites:
        print("No sites found.")
        return

    with sync_playwright() as p:
        # Open one Chromium browser window.
        browser = p.chromium.launch(headless=False)

        # Create one browser context.
        context = browser.new_context()

        # Open the first site in the first tab.
        first = sites[0]
        page = context.new_page()

        print(f"Opening: {first['name']}")
        page.goto(first["url"], wait_until="domcontentloaded", timeout=60000)

        # Open every remaining site in its own tab.
        for site in sites[1:]:
            print(f"Opening: {site['name']}")

            page = context.new_page()

            try:
                page.goto(
                    site["url"],
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
            except Exception as e:
                print(f"  Failed to load: {e}")

        print()
        print(f"Opened {len(sites)} websites.")
        print("The browser will remain open.")
        print("Close the browser window when you're finished.")

        # Keep the Python process alive while the browser is open.
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        browser.close()


if __name__ == "__main__":
    main()
