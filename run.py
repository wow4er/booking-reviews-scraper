import asyncio
import json
import logging

from booking_reviews_scraper.orchestrator import scrape_hotel_reviews
from booking_reviews_scraper.utils import clean_url, load_proxies

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("booking_reviews_scraper")

# Edit these instead of passing CLI flags.

HOTEL_URLS = [
    "https://www.booking.com/hotel/cy/flora-apartments.ro.html",
    # "https://www.booking.com/hotel/us/example-hotel.html",
]

PROXIES_FILE = "proxies.txt"
OUTPUT_FILE = "reviews.jsonl"

MAX_RESULTS = 100  # None means fetch all reviews, or set an int like 200
SORTER = "MOST_RELEVANT"  # NEWEST_FIRST, OLDEST_FIRST, MOST_RELEVANT
LANG = "en-us"
SEARCH_KEYWORDS = []  # e.g. ["noisy", "great staff"], flags matching reviews
CONCURRENCY = 5  # worker sessions per hotel


async def main():
    proxies = load_proxies(PROXIES_FILE)
    urls = [clean_url(u) for u in HOTEL_URLS]

    out_file = open(OUTPUT_FILE, "a", encoding="utf-8")

    async def push_data(batch: list[dict]):
        for item in batch:
            out_file.write(json.dumps(item, ensure_ascii=False) + "\n")
        out_file.flush()
        logger.info(f"Wrote {len(batch)} reviews")

    try:
        for url in urls:
            logger.info(f"Scraping {url}")
            await scrape_hotel_reviews(
                page_url=url,
                desired_count="all" if MAX_RESULTS is None else MAX_RESULTS,
                proxies=proxies,
                push_data=push_data,
                sorter=SORTER,
                lang=LANG,
                search=SEARCH_KEYWORDS,
                max_concurrent=CONCURRENCY,
            )
    finally:
        out_file.close()


if __name__ == "__main__":
    asyncio.run(main())
