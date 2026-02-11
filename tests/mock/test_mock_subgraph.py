import pytest
from unittest.mock import patch
from decimal import Decimal
from bal_tools.models import GqlChain, Pool
from mock_data import mock_responses


def mock_fetch_graphql_data(self, subgraph, query, params=None, url=None):
    assert query in mock_responses, f"Unexpected query: {query}"
    return mock_responses[query]


@pytest.fixture(scope="module")
def date_range():
    return (1728190800, 1729400400)


@patch("bal_tools.subgraph.Subgraph.fetch_graphql_data", mock_fetch_graphql_data)
# TODO:
@pytest.mark.skip(
    "poolGetPool/tokenGetHistoricalPrices mock needs to updated based on new get_twap_price_pool implementation"
)
def test_get_twap_price_token(subgraph, date_range):
    addresses = ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]
    chain = GqlChain.MAINNET
    result = subgraph.get_twap_price_token(addresses, chain, date_range)
    assert result.twap_price == Decimal(150)


@patch("bal_tools.subgraph.Subgraph.fetch_graphql_data", mock_fetch_graphql_data)
# TODO:
@pytest.mark.skip(
    "poolGetPool/tokenGetHistoricalPrices mock needs to updated based on new get_twap_price_pool implementation"
)
def test_get_twap_price_bpt(subgraph, date_range):
    pool_id = "0x5c6ee304399dbdb9c8ef030ab642b10820db8f56000200000000000000000014"
    chain = GqlChain.MAINNET
    result = subgraph.get_twap_price_pool(pool_id, chain, date_range)
    assert result.bpt_price == Decimal(8.5)


@patch("bal_tools.subgraph.Subgraph.fetch_graphql_data", mock_fetch_graphql_data)
def test_fetch_all_pools_info(subgraph):
    result = subgraph.fetch_all_pools_info()
    assert isinstance(result[0], Pool)
    assert len(result) == 1
    pool = result[0]
    assert (
        pool.id == "0xca8ecd05a289b1fbc2e0eaec07360c4bfec07b6100020000000000000000051d"
    )
    assert pool.address == "0xca8ecd05a289b1fbc2e0eaec07360c4bfec07b61"
    assert pool.chain == "ARBITRUM"
    assert pool.type == "GYRO"
    assert pool.symbol == "2CLP-AUSDC-USDC"
    assert pool.gauge.address == "0x75ba7f8733c154302cbe2e19fe3ec417e0679833"
    assert pool.tokens[0].address == "0x7cfadfd5645b50be87d546f42699d863648251ad"
    assert pool.tokens[1].address == "0xaf88d065e77c8cc2239327c5edb3a432268e5831"


@patch("bal_tools.subgraph.Subgraph.fetch_graphql_data", mock_fetch_graphql_data)
def test_get_balancer_pool_snapshots(subgraph):
    block = 12345678
    result = subgraph.get_balancer_pool_snapshots(block=block)
    assert isinstance(result, list)
    assert len(result) == 1
    snapshot = result[0]
    assert snapshot.address == "0xff4ce5aaab5a627bf82f4a571ab1ce94aa365ea6"
    assert (
        snapshot.id
        == "0xff4ce5aaab5a627bf82f4a571ab1ce94aa365ea6000200000000000000000426"
    )
    assert snapshot.symbol == "DOLA-USDC BSP"
    assert snapshot.tokens[0].symbol == "DOLA"
    assert snapshot.tokens[1].symbol == "USDC"
    assert snapshot.timestamp == 1713744000
