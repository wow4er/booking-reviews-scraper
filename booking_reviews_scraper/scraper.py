import logging
import random
from .awswaf.aws import AwsWaf
from curl_cffi import requests
import json
from bs4 import BeautifulSoup
import re
import time
import asyncio
from datetime import datetime

logger = logging.getLogger("booking_reviews_scraper")


QUERY = """query ReviewList($input: ReviewListFrontendInput!, $shouldShowReviewListPhotoAltText: Boolean = false, $shouldGetUserReviewCount: Boolean = false) {
  reviewListFrontend(input: $input) {
    ... on ReviewListFrontendResult {
      ratingScores {
        name
        translation
        value
        ufiScoresAverage {
          ufiScoreLowerBound
          ufiScoreHigherBound
          __typename
        }
        __typename
      }
      topicFilters {
        id
        name
        isSelected
        translation {
          id
          name
          __typename
        }
        __typename
      }
      reviewScoreFilter {
        name
        value
        count
        __typename
      }
      languageFilter {
        name
        value
        count
        countryFlag
        __typename
      }
      timeOfYearFilter {
        name
        value
        count
        __typename
      }
      customerTypeFilter {
        count
        name
        value
        __typename
      }
      roomTypeFilter {
        name
        roomTypeId
        count
        roomIds
        __typename
      }
      reviewCard {
        reviewUrl
        guestDetails {
          username
          avatarUrl
          countryCode
          countryName
          avatarColor
          showCountryFlag
          anonymous
          guestTypeTranslation
          userReviewCount @include(if: $shouldGetUserReviewCount)
          joinedDate @include(if: $shouldGetUserReviewCount)
          __typename
        }
        bookingDetails {
          customerType
          roomId
          roomType {
            id
            name
            __typename
          }
          checkoutDate
          checkinDate
          numNights
          stayStatus
          __typename
        }
        reviewedDate
        isTranslatable
        helpfulVotesCount
        reviewScore
        textDetails {
          title
          positiveText
          negativeText
          textTrivialFlag
          lang
          __typename
        }
        isApproved
        partnerReply {
          reply
          __typename
        }
        positiveHighlights {
          start
          end
          __typename
        }
        negativeHighlights {
          start
          end
          __typename
        }
        editUrl
        photos {
          id
          urls {
            size
            url
            __typename
          }
          kind
          mlTagHighestProbability @include(if: $shouldShowReviewListPhotoAltText)
          __typename
        }
        __typename
      }
      reviewsCount
      sorters {
        name
        value
        __typename
      }
      __typename
    }
    ... on ReviewsFrontendError {
      statusCode
      message
      __typename
    }
    __typename
  }
}
"""


class BookingsReviewsScraper:
    def __init__(self, proxies):
        self.proxy = None
        self.proxies = proxies
        self.session = None
        self.agent_version = random.randint(146, 151)
        self.host = 'd8c14d4960ca.edge.sdk.awswaf.com/d8c14d4960ca/a18a4859af9c'

    async def init_session(self, page_url, max_retries=3):

        for attempt in range(max_retries):
            self.proxy = random.choice(self.proxies)
            self.agent_version = random.randint(146, 151)
            self.session = requests.AsyncSession(
                impersonate="chrome145",
                proxies={
                    "http": f"http://{self.proxy}",
                    "https": f"http://{self.proxy}",
                },
            )
            self.session.headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'priority': 'u=0, i',
                'sec-ch-ua': f'"Google Chrome";v="{self.agent_version}", "Chromium";v="{self.agent_version}", "Not)A;Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.agent_version}.0.0.0 Safari/537.36',
            }

            token = await AwsWaf(self.host, "www.booking.com", agent_version=self.agent_version, proxies=self.proxies)()
            if token:
                params = await self.get_params(page_url=page_url, token=token)
                if params:
                    self.session.headers.update({"cookie": "bkng_sso_ses=e30"})
                    self.session.headers.update({"cookie": "bkng_sso_session=e30"})
                    self.session.headers.update({"cookie": "cors_js=1"})
                    self.session.headers.update({"cookie": "bkng_prue=1"})
                    self.session.headers.update({"cookie": "BJS=-"})
                    self.session.headers.update({"cookie": "pcm_personalization_disabled=0"})

                    return params
            else:
                logger.debug("Retrying to init session")
                try:
                    await self.session.close()
                except Exception as e:
                    logger.debug(f"Error closing session: {e}")

            await asyncio.sleep(random.uniform(1, 2))

        logger.warning(f"Could not init session after {max_retries} attempts")
        return None

    async def get_params(self, page_url, token=None):
        try:
            res = await self.session.get(page_url, allow_redirects=True)

            logger.debug(f"params status: {res.status_code}")
            if res.status_code == 202:

                if 'label='  in res.url:
                    chal_url = res.url + f"chal_t={int(time.time() * 1000)}&force_referer="
                else:
                    chal_url = res.url
                headers2 = {
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'accept-language': 'en-US,en;q=0.8',
                    'cache-control': 'no-cache',
                    'ect': '4g',
                    'pragma': 'no-cache',
                    'priority': 'u=0, i',
                    'referer': chal_url,
                    'sec-ch-ua': f'"Google Chrome";v="{self.agent_version}", "Chromium";v="{self.agent_version}", "Not)A;Brand";v="24"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'document',
                    'sec-fetch-mode': 'navigate',
                    'sec-fetch-site': 'same-origin',
                    'upgrade-insecure-requests': '1',
                    'user-agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.agent_version}.0.0.0 Safari/537.36',
                }
                self.session.headers.update({"cookie": "aws-waf-token=" + token})
                await asyncio.sleep(1)
                res = await self.session.get(chal_url, headers=headers2)
                logger.debug(f"Page status: {res.status_code}")
                if res.status_code < 300:
                    return self.extract_review_params(res.text, chal_url, page_url)
            return None

        except Exception as e:
            logger.warning(f"get_params failed: {e}")
            return None

    def extract_review_params(self, html: str, chal_url: str, page_url: str) -> dict:
        soup = BeautifulSoup(html, 'lxml')

        script_tag = soup.find(
            "script",
            attrs={"data-capla-namespace": re.compile(r"^b-property-web-property-page")},
        )
        if script_tag is None:
            raise ValueError("capla script tag not found")

        data = json.loads(script_tag.string)

        result = {
            "url_orig": page_url,
            "hotel_id": None,
            "ufi": None,
            "hotel_country_code": None,
            "hotel_score": None,
            "reviews_count": None,
            "dest_id": None,
            "dest_type": None,
            "deviceId": None,
            "buid": None,
            "csrf": None,
            "label": None,
            "aff": None,
            "base_page": None,
            "oauth_state": None,
            "ref": chal_url,
            "actionName": None,
            "pageviewId": None,
            "etSerializedState": None,
            "hotel_name": None,
            "accommodation_type": None,
        }

        try:
            context_data = soup.find('script',
                                     {"data-capla-application-context": "data-capla-application-context"}).get_text()
            context_data = json.loads(context_data)
        except:
            context_data = {}

        if context_data:
            unpacked_token = context_data.get('unpackedGuestAccessToken') or {}
            result['deviceId'] = unpacked_token.get('deviceId')
            result['buid'] = unpacked_token.get('buid')
            result['csrf'] = context_data.get('csrfToken')
            affiliate = context_data.get('affiliate') or {}
            result['label'] = affiliate.get('label')
            result['aff'] = affiliate.get('id')
            result['base_page'] = context_data.get('basePageUrl')
            result['oauth_state'] = context_data.get('encryptedCommonOauthState')
            result['etSerializedState'] = context_data.get('etSerializedState')
            result['pageviewId'] = context_data.get('pageviewId')
            result['actionName'] = context_data.get('actionName')

        appolo_id = re.search(r'data-capla-namespace="b-property-web-property-page([^"]+)"', html).group(1)
        result['appolo_id'] = appolo_id
        sid = re.search(r'"b_sid":"([^"]+)"', html).group(1)
        result['sid'] = sid
        def walk(node):
            if isinstance(node, dict):

                if node.get("__typename") == "Property":
                    result["hotel_name"] = node.get("name")
                    ref = node.get("accommodationType", {}).get("__ref", "")
                    match = re.search(r'"type":"([^"]+)"', ref)
                    if match:
                        result["accommodation_type"] = match.group(1)

                if node.get("__typename") == "PropertyReview":
                    total_score = node.get("totalScore")
                    if isinstance(total_score, dict):
                        result["hotel_score"] = total_score.get("score")
                        result["reviews_count"] = total_score.get("reviewsCount")

                if node.get("__typename") == "SearchBoxLocation":
                    result["dest_id"] = node.get("destId")
                    result["dest_type"] = node.get("destType")

                if "hotelId" in node:
                    result["hotel_id"] = node["hotelId"]
                if "ufi" in node and result["ufi"] is None:
                    result["ufi"] = node["ufi"]
                if "countryCode" in node and result["hotel_country_code"] is None:
                    result["hotel_country_code"] = node["countryCode"]

                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(data)

        return result

    async def fetch_reviews(
            self,
            params: dict,
            skip: int,
            sorter: str = "MOST_RELEVANT",
            lang: str = "en-us",
            limit: int = 25,
    ):
        url = "https://www.booking.com/dml/graphql"

        query_params = {
            "label": params["label"],
            "aid": str(params["aff"]),
            "sid": params["sid"],
            "dist": "0",
            "keep_landing": "1",
            "sb_price_type": "total",
            "type": "total",
            "chal_t": str(int(time.time() * 1000)),
            "force_referer": "",
            "lang": lang,
            "soz": "1",
            "lang_changed": "1",
        }

        # self.session.headers.update({"cookie": f"explicit_language_preference={lang}"})

        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'apollographql-client-name': 'b-property-web-property-page',
            'apollographql-client-version': params['appolo_id'],
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'ect': '4g',
            'origin': 'https://www.booking.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': params['ref'],
            'sec-ch-ua': f'"Google Chrome";v="{self.agent_version}", "Chromium";v="{self.agent_version}", "Not)A;Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.agent_version}.0.0.0 Safari/537.36',
            'x-apollo-operation-name': 'ReviewList',
            'x-booking-context-action': params['actionName'],
            'x-booking-context-action-name': params['actionName'],
            'x-booking-context-aid': str(params['aff']),
            'x-booking-csrf-token': params['csrf'],
            'x-booking-et-serialized-state': params['etSerializedState'],
            'x-booking-pageview-id': params['pageviewId'],
            'x-booking-site-type-id': '1',
            'x-booking-timeout-ms': '4000',
            'x-booking-topic': 'capla_browser_b-property-web-property-page',
            'x-envoy-upstream-rq-timeout-ms': '4000',
        }

        payload = {
            "operationName": "ReviewList",
            "variables": {
                "shouldShowReviewListPhotoAltText": True,
                "shouldGetUserReviewCount": True,
                "input": {
                    "hotelId": params['hotel_id'],
                    "ufi": params['ufi'],
                    "hotelCountryCode": params['hotel_country_code'],
                    "sorter": sorter,
                    "filters": {"text": ""},
                    "skip": skip,
                    "limit": limit,
                    "hotelScore": params['hotel_score'],
                    "upsortReviewUrl": "",
                    "searchFeatures": {"destId": params['dest_id'], "destType": "CITY"},
                },
            },
            "extensions": {},
            "query": QUERY,
        }

        resp = await self.session.post(url, params=query_params, headers=headers, json=payload)
        if resp.status_code < 300:
            await asyncio.sleep(random.uniform(0, 1))
        return resp.json()

    async def close(self):
        await self.session.close()


    def process_reviews_response(self, reviews_response, params: dict, search: list):
        reviews_data = []
        rating_statistics_raw = reviews_response['data']["reviewListFrontend"]['ratingScores']
        rating_statistics = {}
        for r in rating_statistics_raw:
            name = r['name']
            try:
                rating_round = round(r['value'], 1)
            except:
                rating_round = None
            name_selected_language = r['translation']
            rating_statistics[name] = {"rating_rounded": rating_round, "rating_orig": r['value'], "name_translated": name_selected_language}

        if 'data' in reviews_response:
            for n, review in enumerate(reviews_response["data"]["reviewListFrontend"]["reviewCard"]):
                hotel_url = params['url_orig']
                hotel_name = params['hotel_name']
                accommodation_type = params['accommodation_type']

                text_details = review.get('textDetails') or {}
                partner_reply = review.get('partnerReply') or {}
                guest_details = review.get('guestDetails') or {}
                booking_details = review.get('bookingDetails') or {}
                room_type = booking_details.get('roomType') or {}

                review_score = review.get('reviewScore')
                review_approved = review.get('isApproved', False)
                review_title = text_details.get('title', '')
                review_positive_text = text_details.get('positiveText', '')
                review_negative_text = text_details.get('negativeText', '')
                review_reply = partner_reply.get('reply')

                guest_username = guest_details.get('username')
                guest_type = guest_details.get('guestTypeTranslation')
                guest_reviews = guest_details.get('userReviewCount')
                guest_country = guest_details.get('countryName')
                guest_country_code = guest_details.get('countryCode')
                guest_avatar = guest_details.get('avatarUrl')
                guest_anonymous = guest_details.get('anonymous')
                guest_join_date_unix = guest_details.get('joinedDate')
                guest_join_date = datetime.fromtimestamp(guest_join_date_unix).strftime(
                    "%Y-%m-%d") if guest_join_date_unix else None

                booking_room = room_type.get('name')
                booking_checkin = booking_details.get('checkinDate')
                booking_checkout = booking_details.get('checkoutDate')
                booking_customer_type = booking_details.get('customerType')
                booking_stay_status = booking_details.get('stayStatus')
                photos_raw = review.get('photos') or []
                review_photos = []
                for photo in photos_raw:
                    urls = photo.get('urls') or []
                    if urls:
                        photo_url = urls[0].get('url')
                        if photo_url:
                            review_photos.append(photo_url)

                keyword_match = False
                matched_keywords = {}
                if search:
                    for s in search:
                        if review_title and s.lower() in review_title.lower():
                            keyword_match = True
                            matched_keywords[s] = 'title'
                        if review_negative_text and s.lower() in review_negative_text.lower():
                            keyword_match = True
                            matched_keywords[s] = 'review_negative_text'
                        if review_positive_text and s.lower() in review_positive_text.lower():
                            keyword_match = True
                            matched_keywords[s] = 'review_positive_text'
                matched_keywords = matched_keywords
                reviews_data.append({
                    "hotel_url": hotel_url,
                    "hotel_name": hotel_name,
                    "accommodation_type": accommodation_type,
                    "review_score": review_score,
                    "review_approved": review_approved,
                    "review_title": review_title,
                    "review_positive_text": review_positive_text,
                    "review_negative_text": review_negative_text,
                    "review_photos": review_photos,
                    "review_reply": review_reply,
                    "guest_username": guest_username,
                    "guest_type": guest_type,
                    "guest_reviews": guest_reviews,
                    "guest_country": guest_country,
                    "guest_country_code": guest_country_code,
                    "guest_avatar": guest_avatar,
                    "guest_anonymous": guest_anonymous,
                    "guest_join_date": guest_join_date,
                    "booking_room": booking_room,
                    "booking_checkin": booking_checkin,
                    "booking_checkout": booking_checkout,
                    "booking_customer_type": booking_customer_type,
                    "booking_stay_status": booking_stay_status,
                    "rating_statistics": rating_statistics,
                    "keyword_match": keyword_match,
                    "matched_keywords": matched_keywords,
                })

        return reviews_data