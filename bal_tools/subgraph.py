from urllib.request import urlopen
from urllib.parse import urlparse
import os
import re
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Union, List, Callable, Dict
import warnings
import numpy as np

import pandas as pd
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from gql.transport.exceptions import TransportServerError
from web3 import Web3

from .utils import get_abi, flatten_nested_dict, chain_ids_by_name
from .models import *
from .errors import NoPricesFoundError
from .ts_config_loader import ts_config_loader
from .etherscan import Etherscan
from ._version import __version__ as VERSION


def url_dict_from_df(df):
    return (
        dict(
            zip(
                df["Network"].str.lower().replace("ethereum", "mainnet"),
                df["Production URL"].str.replace("open in new window", ""),
            )
        ),
        dict(
            zip(
                df["Network"].str.lower().replace("ethereum", "mainnet"),
                df["Development URL (rate-limited)"].str.replace(
                    "open in new window", ""
                ),
            )
        ),
    )


graphql_base_path = f"{os.path.dirname(os.path.abspath(__file__))}/graphql"
vault_df, pools_df = pd.read_html(
    "https://docs.balancer.fi/data-and-analytics/data-and-analytics/subgraph.html",
    match="Network",
    flavor="lxml",
)

SNAPSHOT_URL = "https://hub.snapshot.org/graphql"
AURA_SUBGRAPH_URI = "https://api.subgraph.ormilabs.com/api/public/396b336b-4ed7-469f-a8f4-468e1e26e9a8/subgraphs"
AURA_SUBGRAPHS_BY_CHAIN = {
    "mainnet": f"{AURA_SUBGRAPH_URI}/aura-finance-mainnet/v0.0.1/",
    "arbitrum": f"{AURA_SUBGRAPH_URI}/aura-finance-arbitrum/v0.0.1/",
    "optimism": f"{AURA_SUBGRAPH_URI}/aura-finance-optimism/v0.0.1/",
    "gnosis": f"{AURA_SUBGRAPH_URI}/aura-finance-gnosis/v0.0.3/",
    "base": f"{AURA_SUBGRAPH_URI}/aura-finance-base/v0.0.1/",
    "polygon": f"{AURA_SUBGRAPH_URI}/aura-finance-polygon/v0.0.1/",
    "zkevm": "https://api.studio.thegraph.com/query/77603/aura-finance-zkevm/v0.0.1/",
    "fraxtal": None,
    "avalanche": f"{AURA_SUBGRAPH_URI}/aura-finance-avalanche/v0.0.1/",
    "plasma": None,
}
VAULT_V3_SUBGRAPHS_BY_CHAIN, VAULT_V3_SUBGRAPHS_BY_CHAIN_DEV = url_dict_from_df(
    vault_df
)
POOLS_V3_SUBGRAPHS_BY_CHAIN, POOLS_V3_SUBGRAPHS_BY_CHAIN_DEV = url_dict_from_df(
    pools_df
)


class Subgraph:
    def __init__(self, chain: str = "mainnet", silence_warnings: bool = False):
        if chain not in chain_ids_by_name().keys():
            raise ValueError(f"Invalid chain: {chain}")
        self.chain = chain
        self.subgraph_url = {}
        if silence_warnings:
            self.set_silence_warnings(True)
        self.custom_price_logic: Dict[str, Callable] = {}
        self.etherscan_client = None

    def set_silence_warnings(self, silence_warnings: bool):
        if silence_warnings:
            warnings.filterwarnings("ignore", module="bal_tools.subgraph")
        else:
            warnings.filterwarnings("default", module="bal_tools.subgraph")

    def get_subgraph_url(self, subgraph="core") -> str:
        """
        perform some soup magic to determine the latest subgraph url

        sources used (in order of priority):
        1. sdk config file
        2. frontend v2 config file
        3. frontend v2 config file (legacy style; for chains not supported by decentralised the graph)

        params:
        - subgraph: "apiv3", "vault-v3", "pools-v3", "core", "gauges", "blocks" or "aura"

        returns:
        - https url of the subgraph
        """
        # before anything else, try to get the url from the latest backend config
        if subgraph == "snapshot":
            return SNAPSHOT_URL
        if subgraph == "aura":
            return AURA_SUBGRAPHS_BY_CHAIN.get(self.chain, None)
        url = self.get_subgraph_url_from_backend_config(subgraph)
        if url:
            return url
        if subgraph == "apiv3":
            if self.chain == "sepolia":
                return "https://test-api-v3.balancer.fi"
            return "https://api-v3.balancer.fi"
        if subgraph == "vault-v3":
            return self.get_subgraph_url_vault_v3(self.chain)
        if subgraph == "pools-v3":
            return self.get_subgraph_url_pools_v3(self.chain)
        return (
            self.get_subgraph_url_frontendv2(subgraph)
            or self.get_subgraph_url_legacy(subgraph)
            or self.get_subgraph_url_sdk(subgraph)
            or None
        )

    def get_subgraph_url_from_backend_config(self, subgraph: str) -> str:
        ts_keys_map = {
            "vault-v3": "balancerV3",
            "pools-v3": "balancerPoolsV3",
            "core": "balancer",
            "gauges": "gauge",
            "aura": "aura",
        }
        config_path = f"https://raw.githubusercontent.com/balancer/backend/refs/heads/v3-main/config/{self.chain}.ts"
        try:
            config = ts_config_loader(config_path)
            if subgraph not in ts_keys_map:
                return None
            url = config["subgraphs"][ts_keys_map[subgraph]]
            if not url:
                return None
            if ("${env.THEGRAPH_API_KEY_BALANCER}" in url) or (
                "${env.THEGRAPH_API_KEY_FANTOM}" in url
            ):
                graph_api_key = os.getenv("GRAPH_API_KEY")
                if graph_api_key:
                    try:
                        url = url.replace(
                            "${env.THEGRAPH_API_KEY_BALANCER}",
                            graph_api_key,
                        )
                        url = url.replace(
                            "${env.THEGRAPH_API_KEY_FANTOM}",
                            graph_api_key,
                        )
                        return url
                    except:
                        return None
                else:
                    warnings.warn(
                        f"`GRAPH_API_KEY` not set. may be rate limited or have stale data for subgraph:{subgraph} url:{url}",
                        UserWarning,
                    )
                    return None
            return url
        except:
            return None

    def get_subgraph_url_vault_v3(self, chain: str) -> str:
        graph_api_key = os.getenv("GRAPH_API_KEY")
        if graph_api_key:
            try:
                return VAULT_V3_SUBGRAPHS_BY_CHAIN.get(chain, None).replace(
                    "[api-key]", graph_api_key
                )
            except AttributeError:
                pass
        return VAULT_V3_SUBGRAPHS_BY_CHAIN_DEV.get(chain, None)

    def get_subgraph_url_pools_v3(self, chain: str) -> str:
        graph_api_key = os.getenv("GRAPH_API_KEY")
        if graph_api_key:
            try:
                return POOLS_V3_SUBGRAPHS_BY_CHAIN.get(chain, None).replace(
                    "[api-key]", graph_api_key
                )
            except AttributeError:
                pass
        return POOLS_V3_SUBGRAPHS_BY_CHAIN_DEV.get(chain, None)

    def get_subgraph_url_frontendv2(self, subgraph):
        if subgraph == "core":
            magic_word = "main:"
        elif subgraph == "gauges":
            magic_word = "gauge:"
        elif subgraph == "blocks":
            magic_word = "blocks:"

        # get subgraph url from frontend config
        chain_url_slug = "gnosis-chain" if self.chain == "gnosis" else self.chain
        config_file = f"https://raw.githubusercontent.com/balancer/frontend-v2/master/src/lib/config/{chain_url_slug}/index.ts"
        found_magic_word = False
        try:
            with urlopen(config_file) as f:
                for line in f:
                    if found_magic_word or magic_word + " `" in str(line):
                        # url is on this line
                        r = re.search("`(.*)`", line.decode("utf-8"))
                        try:
                            url = r.group(1)
                            if urlparse(url).scheme in ["http", "https"]:
                                graph_api_key = os.getenv("GRAPH_API_KEY")
                                if "${keys.graph}" in url:
                                    if not graph_api_key:
                                        warnings.warn(
                                            f"`GRAPH_API_KEY` not set. may be rate limited or have stale data for subgraph:{subgraph} url:{url}",
                                            UserWarning,
                                        )
                                        return None
                                    return url.replace("${keys.graph}", graph_api_key)
                                return url
                        except AttributeError:
                            break
                    if magic_word in str(line):
                        # url is on next line, return it on the next iteration
                        found_magic_word = True
        except:
            pass
        return None

    def get_subgraph_url_sdk(self, subgraph):
        if subgraph == "core":
            magic_word = "subgraph:"
        elif subgraph == "gauges":
            magic_word = "gaugesSubgraph:"
        elif subgraph == "blocks":
            magic_word = "blockNumberSubgraph:"

        # get subgraph url from sdk config
        sdk_file = f"https://raw.githubusercontent.com/balancer/balancer-sdk/develop/balancer-js/src/lib/constants/config.ts"
        found_magic_word = False
        urls_reached = False
        try:
            with urlopen(sdk_file) as f:
                for line in f:
                    if "[Network." in str(line):
                        chain_detected = (
                            str(line).split("[Network.")[1].split("]")[0].lower()
                        )
                        if chain_detected == self.chain:
                            for line in f:
                                if "urls: {" in str(line) or urls_reached:
                                    urls_reached = True
                                    if "}," in str(line):
                                        return None
                                    if found_magic_word:
                                        url = (
                                            line.decode("utf-8")
                                            .strip()
                                            .split(",")[0]
                                            .strip(" ,'")
                                        )
                                        url = re.sub(
                                            r"(\s|\u180B|\u200B|\u200C|\u200D|\u2060|\uFEFF)+",
                                            "",
                                            url,
                                        )
                                        if urlparse(url).scheme in ["http", "https"]:
                                            return url
                                    if magic_word in str(line):
                                        # url is on next line, return it on the next iteration
                                        found_magic_word = True
        except:
            pass
        return None

    def get_subgraph_url_legacy(self, subgraph):
        if subgraph == "core":
            magic_word = "main: ["
        elif subgraph == "gauges":
            magic_word = "gauge:"
        elif subgraph == "blocks":
            magic_word = "blocks:"

        chain_url_slug = "gnosis-chain" if self.chain == "gnosis" else self.chain
        config_file = f"https://raw.githubusercontent.com/balancer/frontend-v2/master/src/lib/config/{chain_url_slug}/index.ts"

        found_magic_word = False
        try:
            with urlopen(config_file) as f:
                for line in f:
                    if found_magic_word:
                        url = line.decode("utf-8").strip().strip(" ,'")
                        if urlparse(url).scheme in ["http", "https"]:
                            return url
                    if magic_word + " " in str(line):
                        # url is on same line
                        url = (
                            line.decode("utf-8")
                            .split(magic_word)[1]
                            .strip()
                            .strip(",'")
                        )
                        if urlparse(url).scheme in ["http", "https"]:
                            return url
                    if magic_word in str(line):
                        # url is on next line, return it on the next iteration
                        found_magic_word = True
        except:
            pass
        return None

    def fetch_graphql_data(
        self,
        subgraph: str,
        query: str,
        params: dict = None,
        url: str = None,
        retries: int = 10,
    ):
        """
        query a subgraph using a locally saved query

        params:
        - query: the name of the query (file) to be executed
        - params: optional parameters to be passed to the query
        - retries: number of retry attempts for failed requests (default: 10)

        returns:
        - result of the query
        """
        # build the client
        if not url:
            if not self.subgraph_url.get(subgraph):
                self.subgraph_url[subgraph] = self.get_subgraph_url(subgraph)
                if not self.subgraph_url.get(subgraph):
                    raise ValueError(
                        f"Subgraph url not found for {subgraph} on chain {self.chain}"
                    )

        # prepare the query
        if "{" and "}" in query:
            # `query` is the actual query itself
            gql_query = gql(query)
        else:
            # `query` is the filename; load it from the graphql folder
            with open(f"{graphql_base_path}/{subgraph}/{query}.gql") as f:
                gql_query = gql(f.read())

        # manual retry logic on top of transport retries
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                transport = RequestsHTTPTransport(
                    url=url or self.subgraph_url[subgraph],
                    retries=retries,
                    retry_backoff_factor=2.0,
                    retry_status_forcelist=[400, 429, 500, 502, 503, 504, 520],
                    headers={
                        "x-graphql-client-name": "Maxxis",
                        "x-graphql-client-version": f"bal_tools/v{VERSION}",
                    },
                )
                client = Client(transport=transport, fetch_schema_from_transport=False)
                result = client.execute(gql_query, variable_values=params)
                return result

            except TransportServerError as e:
                error_msg = str(e).lower()
                if "503" in error_msg or "service unavailable" in error_msg:
                    if attempt < max_attempts - 1:
                        wait_time = 30 * (attempt + 1)  # 30s, 60s, 90s
                        time.sleep(wait_time)
                        continue
                raise
            except Exception:
                raise

    def get_first_block_after_utc_timestamp(
        self, timestamp: int, use_etherscan: bool = True
    ) -> int:
        if timestamp > int(datetime.now().strftime("%s")):
            timestamp = int(datetime.now().strftime("%s")) - 2000

        if use_etherscan:
            try:
                if not self.etherscan_client:
                    self.etherscan_client = Etherscan()

                block_number = self.etherscan_client.get_block_by_timestamp(
                    chain=self.chain, timestamp=timestamp, closest="after"
                )

                if block_number:
                    return block_number

            except Exception as e:
                warnings.warn(
                    f"Etherscan V2 block fetch failed for chain {self.chain}: {str(e)}. Falling back to subgraph.",
                    UserWarning,
                )

        try:
            data = self.fetch_graphql_data(
                "blocks",
                "first_block_after_ts",
                {
                    "timestamp_gt": int(timestamp) - 200,
                    "timestamp_lt": int(timestamp) + 200,
                },
            )
            data["blocks"].sort(key=lambda x: x["timestamp"], reverse=True)
            return int(data["blocks"][0]["number"])
        except Exception as e:
            raise Exception(
                f"Failed to fetch block for timestamp {timestamp} on {self.chain}: {str(e)}"
            )

    def filter_outliers_and_average(
        self, prices: List[Decimal], iqr_multiplier: float = 100_000.0
    ) -> Decimal:
        arr = np.array([float(p) for p in prices])

        if len(arr) == 1:
            return prices[0]

        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        bounds = (q1 - iqr_multiplier * iqr, q3 + iqr_multiplier * iqr)
        filtered = arr[(arr >= bounds[0]) & (arr <= bounds[1])]

        return Decimal(str(np.mean(filtered) if len(filtered) > 0 else np.median(arr)))

    def get_twap_price_token(
        self,
        addresses: Union[List[str], str],
        chain: GqlChain,
        date_range: DateRange,
    ) -> Union[TWAPResult, List[TWAPResult]]:
        """
        fetches historical token prices and calculates the TWAP over the given date range.

        :param addresses: list of token addresses or a single address.
        :param chain: chain network from GqlChain enum.
        :param date_range: tuple of (start_date_ts, end_date_ts).
        :return: TWAPResult(s).
        """
        if isinstance(addresses, str):
            addresses = [addresses]

        start_date_ts, end_date_ts = date_range[0], date_range[1]
        current_ts = int(datetime.now(timezone.utc).timestamp())
        one_year_ago_ts = int(
            (datetime.now(timezone.utc) - timedelta(days=365)).timestamp()
        )

        margin = 24 * 3600

        if not (
            one_year_ago_ts - margin <= start_date_ts <= current_ts + margin
            and one_year_ago_ts - margin <= end_date_ts <= current_ts + margin
        ):
            raise ValueError("date range should be within the past year")

        if end_date_ts < start_date_ts:
            raise ValueError("end date should be after start date")

        chain = chain.value if isinstance(chain, GqlChain) else chain.upper()
        params = {"addresses": addresses, "chain": chain, "range": "ONE_YEAR"}

        token_data = self.fetch_graphql_data(
            "apiv3",
            "get_historical_token_prices",
            params,
        )

        def calc_twap(address: str) -> TWAPResult:
            prices = [
                Decimal(item["price"])
                for entry in token_data["tokenGetHistoricalPrices"]
                if entry["address"] == address
                and entry["chain"].lower() == chain.lower()
                for item in entry["prices"]
                if end_date_ts >= int(item["timestamp"]) >= start_date_ts
            ]
            if not prices:
                raise NoPricesFoundError(
                    f"No prices found for {address} on {chain} between {start_date_ts} UTC and {end_date_ts} UTC"
                )
            twap_price = self.filter_outliers_and_average(prices)
            return TWAPResult(address=address, twap_price=twap_price)

        results = [calc_twap(addr) for addr in addresses]
        return results[0] if len(results) == 1 else results

    def get_twap_price_pool(
        self,
        pool_id: str,
        chain: Union[GqlChain, str],
        date_range: DateRange,
    ) -> TwapPrices:
        """
        fetches the TWAP price of a pool's BPT and its tokens over the given `date_range`.

        params:
        - pool_id: the id of the pool
        - chain: the chain network from GqlChain enum
        - date_range: tuple of (start_date_ts, end_date_ts)

        returns:
        - TwapPrices(bpt_price: Decimal, token_prices: List[TWAPResult])
        """

        chain = chain.value if isinstance(chain, GqlChain) else chain.upper()
        params = {
            "chain": chain,
            "id": pool_id,
        }

        token_data = self.fetch_graphql_data(
            "apiv3",
            "get_pool_tokens",
            params,
        )["poolGetPool"]

        token_addresses = [token["address"] for token in token_data["poolTokens"]]
        bpt_address = pool_id[:42]

        bpt_price = self.get_twap_price_token(
            addresses=bpt_address,
            chain=chain,
            date_range=date_range,
        )
        token_prices = self.get_twap_price_token(
            addresses=token_addresses,
            chain=chain,
            date_range=date_range,
        )

        return TwapPrices(bpt_price=bpt_price, token_prices=token_prices)

    def calculate_aura_vebal_share(self, web3: Web3, block_number: int) -> Decimal:
        """
        Function that calculate veBAL share of AURA auraBAL from the total supply of veBAL
        """
        ve_bal_contract = web3.eth.contract(
            address=web3.to_checksum_address(
                "0xC128a9954e6c874eA3d62ce62B468bA073093F25"
            ),
            abi=get_abi("ERC20"),
        )
        total_supply = ve_bal_contract.functions.totalSupply().call(
            block_identifier=block_number
        )
        aura_vebal_balance = ve_bal_contract.functions.balanceOf(
            "0xaF52695E1bB01A16D33D7194C28C42b10e0Dbec2"  # veBAL aura holder
        ).call(block_identifier=block_number)
        return Decimal(aura_vebal_balance) / Decimal(total_supply)

    def fetch_all_pools_info(self) -> List[Pool]:
        """
        Fetches all pools info from balancer graphql api
        """
        res = self.fetch_graphql_data("apiv3", "vebal_get_voting_list")
        return [Pool(**pool) for pool in res["veBalGetVotingList"]]

    def get_balancer_pool_snapshots(
        self,
        block: int = None,
        timestamp: int = None,
        pools_per_req: int = 1000,
        limit: int = 5000,
    ) -> List[PoolSnapshot]:
        if not any([block, timestamp]):
            raise ValueError("Must pass either block or timestamp")

        block = block or self.get_first_block_after_utc_timestamp(timestamp)

        all_pools = []
        offset = 0
        while True:
            result = self.fetch_graphql_data(
                "core",
                "pool_snapshots",
                {"first": pools_per_req, "skip": offset, "block": block},
            )
            all_pools.extend(
                [
                    PoolSnapshot(**flatten_nested_dict(pool))
                    for pool in result["poolSnapshots"]
                ]
            )
            offset += pools_per_req
            if offset >= limit:
                break
            if len(result["poolSnapshots"]) < pools_per_req:
                break
        return all_pools

    def get_v3_protocol_fees(
        self, pool_id: str, chain: GqlChain, date_range: DateRange
    ) -> Decimal:
        """
        Fetches the protocol fees for a given v3 pool over `date range`
        NOTE: assumes `date range` is within a 2 week period
        """
        fee_snapshot = self.fetch_graphql_data(
            "vault-v3",
            "get_protocol_fees",
            {
                "id": pool_id,
                "ts_gt": date_range[0],
                "ts_lt": date_range[1],
                "first": 14,
                "orderBy": "timestamp",
                "orderDirection": "desc",
            },
        )["poolSnapshots"]

        if not fee_snapshot:
            return Decimal(0)

        # descending so first/last snaps are end/start of time window
        end_fee_snapshot, start_fee_snapshot = fee_snapshot[0], fee_snapshot[-1]

        token_addresses = [
            token["address"] for token in end_fee_snapshot["pool"]["tokens"]
        ]

        token_prices = self.get_twap_price_token(
            addresses=token_addresses,
            chain=chain,
            date_range=date_range,
        )

        total_fees = Decimal(0)
        for (
            end_swap_fee,
            end_yield_fee,
            start_swap_fee,
            start_yield_fee,
            twap_token,
        ) in zip(
            end_fee_snapshot["totalProtocolSwapFees"],
            end_fee_snapshot["totalProtocolYieldFees"],
            start_fee_snapshot["totalProtocolSwapFees"],
            start_fee_snapshot["totalProtocolYieldFees"],
            token_prices,
        ):
            swap_fee_diff = Decimal(end_swap_fee) - Decimal(start_swap_fee)
            yield_fee_diff = Decimal(end_yield_fee) - Decimal(start_yield_fee)
            total_fees += (swap_fee_diff + yield_fee_diff) * twap_token.twap_price

        return total_fees

    def get_pool_protocol_version(self, pool_id: str) -> int:
        """
        returns the protocol version for given pool; either 1, 2 or 3
        """
        chain = (
            self.chain.value if isinstance(self.chain, GqlChain) else self.chain.upper()
        )
        params = {
            "chain": chain,
            "id": pool_id,
        }
        res = self.fetch_graphql_data("apiv3", "get_pool_tokens", params)
        return res["poolGetPool"]["protocolVersion"]

    def fetch_pools_by_type(self, pool_types: Union[str, List[str]]) -> List[str]:
        """
        Fetch all pools of specific type(s)
        """
        if isinstance(pool_types, str):
            pool_types = [pool_types]

        result = self.fetch_graphql_data(
            "apiv3",
            "get_core_pools_filters",
            {"where": {"poolTypeIn": pool_types, "chainIn": [self.chain.upper()]}},
        ).get("poolGetPools", [])

        pool_ids = [
            p["id"]
            for p in result
            if float(p.get("dynamicData", {}).get("totalLiquidity", 0)) > 1
        ]

        return pool_ids
