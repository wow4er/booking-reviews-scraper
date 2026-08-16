import asyncio
import logging
import math
from typing import Awaitable, Callable

from .scraper import BookingsReviewsScraper

logger = logging.getLogger("booking_reviews_scraper")

PushCallback = Callable[[list[dict]], Awaitable[None]]


async def scrape_hotel_reviews(
    page_url: str,
    desired_count,          # int or "all"
    proxies: list[str],
    push_data: PushCallback,
    sorter: str = "MOST_RELEVANT",
    lang: str = "en-us",
    max_concurrent: int = 5,
    search: list = [],
    batch_size: int = 100,
    limit: int = 25,
    max_consecutive_errors: int = 10,
):
    """
    Scrapes reviews for a single hotel page, pushing results to push_data in batches.

    Runs several workers concurrently, each holding its own WAF session and proxy.
    When a worker errors out it gets replaced with a fresh session rather than
    retried in place, since a burned session usually stays burned.
    """
    first_worker = BookingsReviewsScraper(proxies)
    logger.info("Preparing WAF sessions, this can take a few seconds")
    params = await first_worker.init_session(page_url)

    if params is None:
        logger.error("Failed to bootstrap session, no params extracted")
        return

    if desired_count == "all":
        workers_needed = max_concurrent
    else:
        pages_needed = math.ceil(int(desired_count) / limit)
        workers_needed = 1 if pages_needed <= 10 else min(max_concurrent, pages_needed)

    worker_queue: asyncio.Queue = asyncio.Queue()
    worker_queue.put_nowait((first_worker, params))

    async def init_worker():
        w = BookingsReviewsScraper(proxies)
        init_params = await w.init_session(page_url)
        return w, init_params

    results = await asyncio.gather(*[init_worker() for _ in range(workers_needed - 1)])

    for w, init_params in results:
        if init_params:
            worker_queue.put_nowait((w, init_params))

    buffer = []
    end_of_data = {"reached": False}

    next_skip = {"value": 0}
    skip_lock = asyncio.Lock()

    scraped_count = {"value": 0}
    target = None if desired_count == "all" else int(desired_count)

    consecutive_errors = {"count": 0}
    errors_lock = asyncio.Lock()

    async def flush_buffer():
        nonlocal buffer
        while len(buffer) >= batch_size:
            batch, buffer = buffer[:batch_size], buffer[batch_size:]
            await push_data(batch)

    async def get_next_skip():
        async with skip_lock:
            if end_of_data["reached"]:
                return None
            if target is not None and next_skip["value"] >= target:
                return None
            skip = next_skip["value"]
            next_skip["value"] += limit
            return skip

    async def worker_loop():
        while True:
            skip = await get_next_skip()
            if skip is None:
                return

            worker, w_params = await worker_queue.get()
            try:
                data = await worker.fetch_reviews(
                    params=w_params,
                    skip=skip,
                    sorter=sorter,
                    lang=lang,
                    limit=limit,
                )
                reviews = data["data"]["reviewListFrontend"]["reviewCard"]

                async with errors_lock:
                    consecutive_errors["count"] = 0

                if not reviews:
                    end_of_data["reached"] = True
                else:
                    buffer.extend(worker.process_reviews_response(data, w_params, search))
                    scraped_count["value"] += len(reviews)
                    await flush_buffer()

                    if len(reviews) < limit:
                        end_of_data["reached"] = True

                worker_queue.put_nowait((worker, w_params))
            except Exception as e:
                logger.warning(f"Skip {skip} failed: {e}")

                async with errors_lock:
                    consecutive_errors["count"] += 1
                    if consecutive_errors["count"] >= max_consecutive_errors:
                        end_of_data["reached"] = True
                        logger.warning("Too many consecutive errors, stopping this hotel")

                await worker.close()
                new_worker = BookingsReviewsScraper(proxies)
                new_params = await new_worker.init_session(page_url)
                if new_params:
                    worker_queue.put_nowait((new_worker, new_params))

    tasks = [asyncio.ensure_future(worker_loop()) for _ in range(workers_needed)]
    await asyncio.gather(*tasks)

    if buffer:
        await push_data(buffer)

    while not worker_queue.empty():
        w, _ = worker_queue.get_nowait()
        await w.close()

    logger.info(f"Done, {scraped_count['value']} reviews scraped for {page_url}")
