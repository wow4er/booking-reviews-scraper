import random, json
from curl_cffi import requests
from .verify import CHALLENGE_TYPES
from .fingerprint import get_fp
from curl_cffi import CurlMime

class AwsWaf:
    def __init__(self,
                 endpoint: str,
                 domain: str,
                 agent_version: int = 149,
                 proxies: list = []
                 ):
        self.agent_version = agent_version
        self.session = requests.AsyncSession(impersonate="chrome145")
        self.session.headers = {
            "connection": "keep-alive",
            "sec-ch-ua-platform": "\"Windows\"",
            "user-agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{agent_version}.0.0.0 Safari/537.36",
            "sec-ch-ua": f'"Google Chrome";v="{agent_version}", "Chromium";v="{agent_version}", "Not)A;Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "accept": "*/*",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9"
        }
        if proxies:
            self.proxy = random.choice(proxies)
            self.session.proxies={
                    "http": f"http://{self.proxy}",
                    "https": f"http://{self.proxy}",
                }
        self.domain = domain
        self.endpoint = endpoint



    async def get_inputs(self):
        r = await self.session.get(f"https://{self.endpoint}/inputs?client=browser")
        return r.json()

    def build_payload(self, inputs: dict):
        checksum, fp = get_fp(self.agent_version)
        return {
            "challenge": inputs['challenge'],
            "solution": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==",
            "signals": [{"name": "Zoey", "value": {"Present": fp}}],
            "checksum": checksum,
            "existing_token": None,
            "client": "Browser",
            "domain": self.domain,
            "metrics": [
                {
                    "name": "2",
                    "value": random.uniform(0, 1),
                    "unit": "2"
                },
                {
                    "name": "100",
                    "value": 0,
                    "unit": "2"
                },
                {
                    "name": "101",
                    "value": 0,
                    "unit": "2"
                },
                {
                    "name": "102",
                    "value": 0,
                    "unit": "2"
                },
                {
                    "name": "103",
                    "value": 8,
                    "unit": "2"
                },
                {
                    "name": "104",
                    "value": 0,
                    "unit": "2"
                },
                {
                    "name": "105",
                    "value": 0,
                    "unit": "2"
                },
                {
                    "name": "106",
                    "value": 0,
                    "unit": "2"
                },
                {
                    "name": "107",
                    "value": 0,
                    "unit": "2"
                },
                {
                    "name": "108",
                    "value": 1,
                    "unit": "2"
                },
                {
                    "name": "undefined",
                    "value": 0,
                    "unit": "2"
                },
                {
                    "name": "110",
                    "value": 0,
                    "unit": "2"
                },
                {
                    "name": "111",
                    "value": 2,
                    "unit": "2"
                },
                {
                    "name": "112",
                    "value": 0,
                    "unit": "2"
                },
                {
                    "name": "undefined",
                    "value": 0,
                    "unit": "2"
                },
                {
                    "name": "3",
                    "value": random.uniform(4, 4.800000011920929),
                    "unit": "2"
                },
                {
                    "name": "7",
                    "value": 0,
                    "unit": "4"
                },
                {
                    "name": "1",
                    "value": random.uniform(10, 20),
                    "unit": "2"
                },
                {
                    "name": "4",
                    "value": 36.5,
                    "unit": "2"
                },
                {
                    "name": "5",
                    "value": random.uniform(0, 1),
                    "unit": "2"
                },
                {
                    "name": "6",
                    "value": random.uniform(50, 60),
                    "unit": "2"
                },
                {
                    "name": "0",
                    "value": random.uniform(130, 140),
                    "unit": "2"
                },
                {
                    "name": "8",
                    "value": 1,
                    "unit": "4"
                }
            ]
        }

    async def verify(self, payload):
        self.session.headers = {
            "connection": "keep-alive",
            "sec-ch-ua-platform": "\"Windows\"",
            "user-agent": f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.agent_version}.0.0.0 Safari/537.36',
            "sec-ch-ua": f'"Google Chrome";v="{self.agent_version}", "Chromium";v="{self.agent_version}", "Not)A;Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "accept": "*/*",
            "origin": "https://www.trustpilot.com",
            "referer": "https://www.trustpilot.com",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9"
        }
        mp = CurlMime()
        mp.addpart(name="solution_metadata", data=json.dumps(payload).encode())
        mp.addpart(name="solution_data", data=payload["solution"].encode())

        res = await self.session.post(f"https://{self.endpoint}/mp_verify", multipart=mp)
        return res.json()["token"]


    async def __call__(self):
        inputs = await self.get_inputs()
        payload = self.build_payload(inputs)
        return await self.verify(payload)
