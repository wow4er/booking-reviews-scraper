# Booking Reviews Scraper

Pure HTTP scraper for booking.com hotel reviews, no browser or headless automation, bypasses AWS WAF and talks directly to the internal GraphQL API

Scrapes hotel reviews from booking.com. It talks directly to the internal GraphQL API booking.com's own frontend uses, so it gets structured review data without touching an HTML parser for the review content itself, and paginates through the full review list for a hotel.

## How it works

Booking.com puts every visitor behind AWS WAF before serving the property page. To get past that, the scraper first solves the WAF challenge for a fresh session, then loads the hotel page to pull out a handful of internal identifiers (hotel id, ufi, csrf token and a few others). Those identifiers get sent along with every GraphQL request to `/dml/graphql`, which is the same endpoint the site's own review widget calls.

The WAF challenge solving lives in `booking_reviews_scraper/awswaf/`. `scraper.py` calls `AwsWaf(host, target_domain, agent_version, proxies)()`, which returns the `aws-waf-token` cookie value needed to get past the challenge page, or `None` if the solve failed. Everything downstream, session init, param extraction, GraphQL requests, depends on getting that token first.

Each worker holds one session tied to one proxy. Multiple workers run in parallel, each paging through a different chunk of the review list with the `skip` and `limit` parameters. If a session gets blocked or a request fails, that worker closes and gets replaced with a new one rather than retried, since a flagged session usually stays flagged.

## Install

```bash
git clone https://github.com/yourname/booking-reviews-scraper
cd booking-reviews-scraper
pip install -e .
```

Requires Python 3.10 or newer.

## Proxies

The scraper needs proxies, booking.com blocks unproxied automation fast. Put yours in a text file, one per line. The proxy string gets inserted directly after `http://` when building the request, so the format has to match what curl_cffi accepts there:

```
1.2.3.4:8080
user:pass@5.6.7.8:8080
```

Lines starting with `#` and blank lines are skipped. There is no parsing beyond reading lines, whatever you put in the file is passed straight through. If the file is missing or has no usable proxies, the scraper stops and prints an error instead of running unproxied.

## CLI usage

```bash
booking-reviews-scraper "https://www.booking.com/hotel/cy/flora-apartments.ro.html" --proxies proxies.txt
```

This writes reviews as JSON lines to `reviews.jsonl` in the current directory.

Common options:

```bash
booking-reviews-scraper URL1 URL2 \
  --proxies proxies.txt \
  --output hotel_reviews.jsonl \
  --max-results 500 \
  --lang en-us \
  --sorter MOST_RELEVANT \
  --search "noisy" "great staff" \
  --concurrency 5
```

- `--max-results` caps how many reviews to fetch per hotel. Leave it out to fetch everything.
- `--search` flags reviews whose title or text contains any of the given keywords. Each matching review gets `keyword_match: true` and a `matched_keywords` map showing where the match happened.
- `--concurrency` controls how many worker sessions run at once per hotel. Higher means faster scraping but more proxy load and a higher chance of getting a proxy flagged.

Run `booking-reviews-scraper --help` for the full list.

## Plain script

If you don't want to deal with CLI flags, `run.py` has the same options as plain variables at the top of the file, edit those and run it directly:

```bash
python run.py
```

## Using it as a library

```python
import asyncio
from booking_reviews_scraper import scrape_hotel_reviews
from booking_reviews_scraper.utils import load_proxies

async def main():
    proxies = load_proxies("proxies.txt")
    collected = []

    async def push_data(batch):
        collected.extend(batch)

    await scrape_hotel_reviews(
        page_url="https://www.booking.com/hotel/cy/flora-apartments.ro.html",
        desired_count=100,
        proxies=proxies,
        push_data=push_data,
    )

    print(f"Got {len(collected)} reviews")

asyncio.run(main())
```

`push_data` is called with a list of review dicts every time the internal buffer fills up, plus once more at the end with whatever is left. Write your own callback to push into a database, a queue, or wherever the data needs to go instead of a file.

## Output fields

Each review is a flat dict with these fields:

| Field | Description |
|---|---|
| `hotel_url` | Cleaned URL of the hotel page |
| `hotel_name` | Hotel name |
| `accommodation_type` | Hotel, apartment, hostel, etc |
| `review_score` | Numeric score the guest gave |
| `review_approved` | Whether booking.com approved the review for display |
| `review_title` | Review title |
| `review_positive_text` | The "liked" part of the review |
| `review_negative_text` | The "disliked" part of the review |
| `review_photos` | List of photo URLs attached to the review |
| `review_reply` | Property owner's reply, if any |
| `guest_username` | Reviewer's display name |
| `guest_type` | Traveler type translation, e.g. "Couple", "Family with young children" |
| `guest_reviews` | How many reviews this guest has written |
| `guest_country` | Reviewer's country name |
| `guest_country_code` | Reviewer's country code |
| `guest_avatar` | URL of the reviewer's avatar image |
| `guest_anonymous` | Whether the review was posted anonymously |
| `guest_join_date` | When the reviewer joined booking.com |
| `booking_room` | Room type booked |
| `booking_checkin`, `booking_checkout` | Stay dates |
| `booking_customer_type` | Type of booking, e.g. solo, business |
| `booking_stay_status` | Whether the stay is confirmed as having happened |
| `rating_statistics` | Hotel-level rating breakdown (cleanliness, location, staff, etc), same for every review of that hotel |
| `keyword_match`, `matched_keywords` | Only meaningful if `--search` was used |

## Extending it

`extract_review_params` in `scraper.py` pulls the bare minimum needed to call the GraphQL endpoint: hotel id, ufi, csrf token, and a handful of similar identifiers. It gets all of this from one script tag in the page, `<script data-capla-namespace="b-property-web-property-page...">`, which holds booking.com's own Apollo GraphQL cache for the page as a JSON blob.

That blob has a lot more in it than what's currently extracted, room prices, amenities, facility lists, nearby landmarks, policy details, and so on. If you need hotel-level data beyond reviews, that script tag plus the rest of the page DOM is the place to look. The `walk()` function inside `extract_review_params` already recurses through the whole JSON structure matching on `__typename`, so adding a new field usually means adding one more `if node.get("__typename") == "...":` branch there.

## Notes

- The scraper impersonates Chrome via curl_cffi's TLS fingerprinting, this matters for getting past the WAF challenge in the first place.
- Language codes follow booking.com's own scheme, `en-us`, `en-gb`, `de`, `fr`, and so on.
- This project is for personal and research use. Check booking.com's terms of service before scraping at any real volume, and keep request rates reasonable.
