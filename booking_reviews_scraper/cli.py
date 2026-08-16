import argparse
import asyncio
import json
import logging

from .orchestrator import scrape_hotel_reviews
from .utils import clean_url, load_proxies

logger = logging.getLogger("booking_reviews_scraper")


def parse_args():
    parser = argparse.ArgumentParser(description="Scrape reviews from booking.com hotel pages")
    parser.add_argument("urls", nargs="+", help="One or more booking.com hotel page URLs")
    parser.add_argument("--proxies", required=True, help="Path to a proxies file, one proxy per line")
    parser.add_argument("--output", default="reviews.jsonl", help="Output file, JSON lines format")
    parser.add_argument("--max-results", type=int, default=None, help="Max reviews per hotel, default is all")
    parser.add_argument("--sorter", default="MOST_RELEVANT", help="Booking.com sort order for reviews")
    parser.add_argument("--lang", default="en-us", help="Language code for review text")
    parser.add_argument("--search", nargs="*", default=[], help="Keywords to flag matching reviews")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrent worker sessions per hotel")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


async def run():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        proxies = load_proxies(args.proxies)
    except FileNotFoundError:
        logger.error(f"Proxies file not found: {args.proxies}")
        return
    except ValueError as e:
        logger.error(str(e))
        return

    urls = [clean_url(u) for u in args.urls]

    out_file = open(args.output, "a", encoding="utf-8")

    async def push_data(batch: list[dict]):
        for item in batch:
            out_file.write(json.dumps(item, ensure_ascii=False) + "\n")
        out_file.flush()
        logger.info(f"Wrote {len(batch)} reviews, {out_file.tell()} bytes so far")

    try:
        for url in urls:
            logger.info(f"Scraping {url}")
            await scrape_hotel_reviews(
                page_url=url,
                desired_count="all" if args.max_results is None else args.max_results,
                proxies=proxies,
                push_data=push_data,
                sorter=args.sorter,
                lang=args.lang,
                search=args.search,
                max_concurrent=args.concurrency,
            )
    finally:
        out_file.close()


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
