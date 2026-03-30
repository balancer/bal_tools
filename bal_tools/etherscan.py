import os
import time
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .utils import chain_ids_by_name


class Etherscan:
    BASE_URL = "https://api.etherscan.io/v2/api"
    # can be removed if official support is added by etherscan or a dedicated blocks subgraph is added
    # no api key needed
    # https://github.com/balancer/bal_tools/pull/137
    PLASMA_API_URL = (
        "https://api.routescan.io/v2/network/mainnet/evm/9745/etherscan/api"
    )

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ETHERSCAN_API_KEY")

        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.last_request_time = 0
        self.rate_limit_delay = 0.2  # 200ms

    def _get_chain_id(self, chain: str) -> int:
        chain_ids = chain_ids_by_name()
        if chain not in chain_ids:
            raise ValueError(
                f"Unsupported chain: {chain}. Supported chains: {list(chain_ids.keys())}"
            )
        return chain_ids[chain]

    def _rate_limit(self):
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last_request)
        self.last_request_time = time.time()

    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self._rate_limit()

        params["apikey"] = self.api_key

        response = self.session.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data.get("status") == "0" and data.get("message") != "No records found":
            raise Exception(
                f"Etherscan API error: {data.get('message', 'Unknown error')}"
            )

        return data

    def _get_block_by_timestamp_plasma(
        self, timestamp: int, closest: str = "before"
    ) -> Optional[int]:
        params = {
            "module": "block",
            "action": "getblocknobytime",
            "timestamp": timestamp,
            "closest": closest,
        }

        try:
            response = self.session.get(self.PLASMA_API_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "1" and data.get("result"):
                return int(data["result"])

            return None

        except Exception as e:
            raise Exception(
                f"Error fetching block for timestamp {timestamp} on plasma: {str(e)}"
            )

    def _get_block_by_timestamp_routescan(
        self, chain_id: int, timestamp: int, closest: str = "before"
    ) -> Optional[int]:
        routescan_url = (
            f"https://api.routescan.io/v2/network/mainnet/evm/{chain_id}/etherscan/api"
        )
        params = {
            "module": "block",
            "action": "getblocknobytime",
            "timestamp": timestamp,
            "closest": closest,
        }
        response = self.session.get(routescan_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "1" and data.get("result"):
            return int(data["result"])

        return None

    def get_block_by_timestamp(
        self, chain: str, timestamp: int, closest: str = "before"
    ) -> Optional[int]:
        if chain == "plasma":
            return self._get_block_by_timestamp_plasma(timestamp, closest)

        if not self.api_key:
            raise ValueError(
                "Etherscan API key required for non-plasma chains. Set ETHERSCAN_API_KEY environment variable or pass api_key parameter"
            )

        chain_id = self._get_chain_id(chain)

        params = {
            "chainid": chain_id,
            "module": "block",
            "action": "getblocknobytime",
            "timestamp": timestamp,
            "closest": closest,
        }

        try:
            data = self._make_request(params)

            if data.get("status") == "1" and data.get("result"):
                return int(data["result"])

            return None

        except Exception as etherscan_error:
            # if etherscan fails, try routescan as fallback
            try:
                return self._get_block_by_timestamp_routescan(
                    chain_id, timestamp, closest
                )
            except Exception:
                # if routescan also fails, raise the original etherscan error
                raise Exception(
                    f"Error fetching block for timestamp {timestamp} on {chain}: {str(etherscan_error)}"
                )
