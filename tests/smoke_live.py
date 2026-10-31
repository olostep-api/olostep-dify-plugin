"""Live check of every tool against the Olostep API.

Reads OLOSTEP_API_KEY from the environment or from .env. Uses a few credits.
Run with: uv run python tests/smoke_live.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from olostep_client.client import OlostepClient, OlostepError  # noqa: E402


def load_key() -> str:
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            if line.startswith("OLOSTEP_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    return os.environ.get("OLOSTEP_API_KEY", "")


def main() -> None:
    client = OlostepClient(load_key())

    client.check_key()
    print("check_key: valid key accepted")
    try:
        OlostepClient("invalid-key").check_key()
        print("check_key: FAILED, invalid key was accepted")
    except OlostepError:
        print("check_key: invalid key rejected")

    page = client.scrape("https://example.com")
    print("scrape:", len(page["markdown"] or ""), "chars")

    search = client.search("Olostep web scraping API", 3)
    print("search:", [r.get("url") for r in search["results"]])

    answer = client.answer("What is the latest stable version of Next.js?")
    print("answer:", str(answer["answer"])[:120], "| sources:", len(answer["sources"]))

    site = client.map("https://docs.olostep.com", 5)
    print("map:", site["urls"])

    crawl = client.crawl("https://docs.olostep.com", 2, 180)
    print("crawl:", crawl["status"], [(p["url"], len(p.get("markdown") or "")) for p in crawl.get("pages", [])])

    batch = client.batch_scrape(["https://example.com", "https://docs.olostep.com"], 180)
    print("batch:", batch["status"], [(p["url"], len(p.get("markdown") or "")) for p in batch.get("pages", [])])

    again = client.results(crawl["id"], 0)
    print("get_results:", again["status"], len(again.get("pages", [])), "pages")


if __name__ == "__main__":
    main()
