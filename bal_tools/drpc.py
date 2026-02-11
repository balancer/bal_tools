from requests import Session
from requests.adapters import HTTPAdapter, Retry
from web3 import Web3

DRPC_NAME_OVERRIDES = {
    "mainnet": "ethereum",
    "zkevm": "polygon-zkevm",
    "hyperevm": "hyperliquid",
    "monad": "monad-mainnet",
}
ADAPTER = HTTPAdapter(
    pool_connections=20,
    pool_maxsize=20,
    max_retries=Retry(
        total=10,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504, 520],
    ),
)
DRPC_SESSION = Session()
DRPC_SESSION.mount("https://", ADAPTER)


class Web3RpcByChain:
    def __init__(self, DRPC_KEY):
        self.DRPC_KEY = DRPC_KEY
        self._w3_by_chain = {}

    def __getitem__(self, chain):
        return self._get_or_create_w3(chain)

    def __getattr__(self, chain):
        return self._get_or_create_w3(chain)

    def _get_or_create_w3(self, chain):
        if chain not in self._w3_by_chain:
            w3 = Web3Rpc(chain, self.DRPC_KEY)
            self._w3_by_chain[chain] = w3
        return self._w3_by_chain[chain]

    def __setitem__(self, chain, value):
        self._w3_by_chain[chain] = value

    def __delitem__(self, chain):
        del self._w3_by_chain[chain]

    def __iter__(self):
        return iter(self._w3_by_chain)

    def keys(self):
        return self._w3_by_chain.keys()

    def values(self):
        return self._w3_by_chain.values()

    def items(self):
        return self._w3_by_chain.items()


class Web3Rpc:
    def __init__(self, chain, DRPC_KEY):
        drpc_chain = DRPC_NAME_OVERRIDES.get(chain, chain)
        endpoint_uri = (
            f"https://lb.drpc.live/ogrpc?network={drpc_chain}&dkey={DRPC_KEY}"
        )
        try:
            self.w3 = Web3(
                Web3.HTTPProvider(endpoint_uri=endpoint_uri, session=DRPC_SESSION)
            )
        except Exception as e:
            raise ConnectionError(
                f"Error connecting to {drpc_chain} on DRPC (url: {endpoint_uri}): {e}"
            )
        if not self.w3.is_connected():
            raise ConnectionError(
                f"Not connected to {drpc_chain} on DRPC (url: {endpoint_uri})"
            )
        try:
            self.w3.eth.block_number
        except Exception as e:
            raise ConnectionError(
                f"Error fetching latest block number: {e}, chain: {chain}, url: {self.w3.provider.endpoint_uri}"
            )

    def __getattr__(self, name):
        return getattr(self.w3, name)
