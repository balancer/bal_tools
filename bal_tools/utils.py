from web3 import Web3
from typing import Union, List, Dict
import json
from importlib.resources import files

import requests


CHAINS = requests.get(
    "https://raw.githubusercontent.com/balancer/bal_addresses/refs/heads/main/extras/chains.json"
).json()


### These functions are to deal with differing web3 versions and the need to use 5.x for legacy brownie code
def to_checksum_address(address: str):
    if hasattr(Web3, "toChecksumAddress"):
        return Web3.toChecksumAddress(address)
    if hasattr(Web3, "to_checksum_address"):
        return Web3.to_checksum_address(address)


def is_address(address: str):
    if hasattr(Web3, "isAddress"):
        return Web3.isAddress(address)
    if hasattr(Web3, "is_address"):
        return Web3.is_address(address)


def get_abi(contract_name: str) -> Union[Dict, List[Dict]]:
    abi_path = files(__package__).joinpath(f"abi/{contract_name}.json")
    with open(abi_path) as f:
        return json.load(f)


def flatten_nested_dict(d):
    result = d.copy()
    for key, value in list(result.items()):
        if isinstance(value, dict):
            if key not in ["dynamicData", "staking"]:
                result.pop(key)
                result.update(value)
    return result


def chain_ids_by_name():
    return CHAINS["CHAIN_IDS_BY_NAME"]


def chain_names_prod():
    return CHAINS["BALANCER_PRODUCTION_CHAINS"]


def chain_names_prod_v3():
    return CHAINS["BALANCER_PRODUCTION_CHAINS_V3"]
