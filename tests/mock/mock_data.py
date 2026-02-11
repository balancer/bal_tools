MOCK_FIRST_BLOCK_AFTER_TS = {
    "blocks": [{"number": "12345678", "timestamp": "1708607101"}]
}

MOCK_HISTORICAL_TOKEN_PRICES = {
    "tokenGetHistoricalPrices": [
        {
            "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "chain": "MAINNET",
            "prices": [
                {
                    "timestamp": "1700000000",
                    "price": 100,
                    "updatedAt": 1700000000,
                },
                {
                    "timestamp": "1700500000",
                    "price": 200,
                    "updatedAt": 1700500000,
                },
            ],
        },
        {
            "address": "0xba100000625a3754423978a60c9317c58a424e3D",
            "chain": "MAINNET",
            "prices": [
                {
                    "timestamp": "1700000000",
                    "price": 300,
                    "updatedAt": 1700000000,
                },
                {
                    "timestamp": "1700500000",
                    "price": 400,
                    "updatedAt": 1700500000,
                },
            ],
        },
    ]
}

MOCK_POOL_TOKENS = {
    "poolGetPool": {
        "dynamicData": {"totalShares": "1000"},
        "poolTokens": [
            {
                "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "balance": "10",
            },
            {
                "address": "0xba100000625a3754423978a60c9317c58a424e3D",
                "balance": "20",
            },
        ],
    }
}

MOCK_VEBAL_GET_VOTING_LIST = {
    "veBalGetVotingList": [
        {
            "id": "0xca8ecd05a289b1fbc2e0eaec07360c4bfec07b6100020000000000000000051d",
            "address": "0xca8ecd05a289b1fbc2e0eaec07360c4bfec07b61",
            "chain": "ARBITRUM",
            "type": "GYRO",
            "symbol": "2CLP-AUSDC-USDC",
            "gauge": {
                "address": "0x75ba7f8733c154302cbe2e19fe3ec417e0679833",
                "isKilled": False,
                "relativeWeightCap": "1.0",
                "addedTimestamp": 1712006855,
                "childGaugeAddress": "0xe39feeb09c4dde420eaaadd066f949ab84c94bb8",
            },
            "tokens": [
                {
                    "address": "0x7cfadfd5645b50be87d546f42699d863648251ad",
                    "logoURI": "https://raw.githubusercontent.com/balancer/tokenlists/main/src/assets/images/tokens/0xe719aef17468c7e10c0c205be62c990754dff7e5.png",
                    "symbol": "AaveUSDCn",
                    "weight": None,
                },
                {
                    "address": "0xaf88d065e77c8cc2239327c5edb3a432268e5831",
                    "logoURI": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/ethereum/assets/0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48/logo.png",
                    "symbol": "USDC",
                    "weight": None,
                },
            ],
        }
    ]
}

MOCK_POOL_SNAPSHOTS = {
    "poolSnapshots": [
        {
            "pool": {
                "address": "0xff4ce5aaab5a627bf82f4a571ab1ce94aa365ea6",
                "id": (
                    "0xff4ce5aaab5a627bf82f4a571ab1ce94aa365ea6000200000000000000000426"
                ),
                "symbol": "DOLA-USDC BSP",
                "totalProtocolFeePaidInBPT": None,
                "tokens": [
                    {
                        "symbol": "DOLA",
                        "address": "0x865377367054516e17014ccded1e7d814edc9ce4",
                        "paidProtocolFees": "16082.944140240944392276",
                    },
                    {
                        "symbol": "USDC",
                        "address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                        "paidProtocolFees": "4706.131322",
                    },
                ],
            },
            "timestamp": 1713744000,
        }
    ]
}

mock_responses = {
    "first_block_after_ts": MOCK_FIRST_BLOCK_AFTER_TS,
    "get_historical_token_prices": MOCK_HISTORICAL_TOKEN_PRICES,
    "get_pool_tokens": MOCK_POOL_TOKENS,
    "vebal_get_voting_list": MOCK_VEBAL_GET_VOTING_LIST,
    "pool_snapshots": MOCK_POOL_SNAPSHOTS,
}
