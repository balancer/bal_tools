import pytest
import json
import os

from bal_tools.pools_gauges import BalPoolsGauges
from bal_tools.subgraph import Subgraph
from bal_tools.ecosystem import Aura
from bal_tools.safe_tx_builder import SafeTxBuilder
from bal_tools.utils import chain_ids_by_name, chain_names_prod, chain_names_prod_v3

from dotenv import load_dotenv
from bal_tools.drpc import Web3Rpc


load_dotenv()

exempt_chains = ["fantom", "goerli", "sonic", "monad"]
chains = [chain for chain in list(chain_ids_by_name()) if chain not in exempt_chains]


@pytest.fixture(scope="module")
def web3():
    return Web3Rpc("mainnet", os.getenv("DRPC_KEY")).w3


@pytest.fixture(scope="module", params=chains)
def chain(request):
    chain = request.param
    return chain


@pytest.fixture(scope="module")
def chains_prod():
    return chain_names_prod()


@pytest.fixture(scope="module")
def chains_prod_v3():
    return chain_names_prod_v3()


@pytest.fixture(scope="module")
def bal_pools_gauges(chain):
    return BalPoolsGauges(chain)


@pytest.fixture(scope="module")
def subgraph_all_chains(chain):
    return Subgraph(chain)


@pytest.fixture(scope="module")
def subgraph():
    return Subgraph()


@pytest.fixture(scope="module")
def aura(chain):
    return Aura(chain)


@pytest.fixture(scope="module")
def safe_tx_builder() -> SafeTxBuilder:
    return SafeTxBuilder("0x10A19e7eE7d7F8a52822f6817de8ea18204F2e4f")


@pytest.fixture(scope="module")
def erc20_abi():
    with open("tests/abi/erc20.json", "r") as file:
        return json.load(file)


@pytest.fixture(scope="module")
def bribe_market_abi():
    with open("tests/abi/bribe_market.json", "r") as file:
        return json.load(file)


@pytest.fixture(scope="module")
def bridge_abi():
    with open("tests/abi/bridge.json", "r") as file:
        return json.load(file)


@pytest.fixture(scope="module")
def reward_distributor_abi():
    with open("tests/abi/RewardDistributor.json", "r") as file:
        return json.load(file)


@pytest.fixture(scope="module")
def stakedao_marketv2_abi():
    with open("tests/abi/stakedao_marketv2.json", "r") as file:
        return json.load(file)


@pytest.fixture(scope="module")
def pool_snapshot_blocks():
    return {
        "arbitrum": 200000000,
        "mainnet": 17000000,
        "polygon": 44000000,
        "gnosis": 28000000,
        "base": 14000000,
        "avalanche": 30000000,
        "zkevm": 1200000,
    }


@pytest.fixture(scope="module")
def DRPC_KEY():
    return os.getenv("DRPC_KEY")


@pytest.fixture(scope="module")
def mainnet_core_pools():
    return BalPoolsGauges().core_pools
