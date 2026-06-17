"""
Tests for ts_config_loader module.

This test validates that the ts_config_loader can successfully parse
all TypeScript configuration files from the Balancer backend repository.
"""

import requests
from bal_tools.ts_config_loader import (
    ts_config_loader,
    _to_json,
    _extract_object_literal,
)


def test_spread_of_imported_identifiers():
    """Regression: spreads of imported identifiers (e.g. workerJobs:
    [...activeChainWorkerJobsGeneric]) must not break JSON parsing.

    The backend network configs import worker-job arrays and spread them into
    `workerJobs`. The parser can't resolve those imports, so it should drop the
    spreads and still produce a valid object rather than raising JSONDecodeError.
    """
    import json

    ts = """
import { activeChainWorkerJobsGeneric, activeChainWorkerJobsV2 } from './worker-jobs';

export default <NetworkData>{
    chain: {
        slug: 'mychain',
    },
    subgraphs: {
        balancer: `https://example.com/v2-mychain-smol/latest/gn`,
        gauge: `https://example.com/balancer-gauges-mychain/latest/gn`,
    },
    workerJobs: [...activeChainWorkerJobsGeneric, ...activeChainWorkerJobsV2],
};
"""
    parsed = json.loads(_to_json(_extract_object_literal(ts)))
    assert parsed["workerJobs"] == []
    assert parsed["subgraphs"]["balancer"].endswith("v2-mychain-smol/latest/gn")
    assert parsed["chain"]["slug"] == "mychain"


def test_spread_of_import_mixed_with_literal():
    """A spread of an import mixed with real array entries should drop only the
    unresolved spread and keep the literal values."""
    import json

    ts = """
import { extraJobs } from './worker-jobs';

export default <NetworkData>{
    stakingServices: ['gauge', ...extraJobs],
    workerJobs: [...extraJobs, 'literalJob'],
};
"""
    parsed = json.loads(_to_json(_extract_object_literal(ts)))
    assert parsed["stakingServices"] == ["gauge"]
    assert parsed["workerJobs"] == ["literalJob"]


def test_all_backend_configs_load():
    """Test that all config files from Balancer backend can be loaded without errors."""

    # Get list of config files from GitHub API
    api_url = (
        "https://api.github.com/repos/balancer/backend/contents/config?ref=v3-main"
    )
    response = requests.get(api_url)
    response.raise_for_status()

    files = response.json()

    # Filter for .ts files (excluding index.ts)
    config_files = [
        f["name"]
        for f in files
        if f["name"].endswith(".ts") and f["name"] != "index.ts"
    ]

    assert len(config_files) > 0, "No config files found"

    failed_configs = []

    loaded_any = False
    for config_file in config_files:
        chain = config_file.replace(".ts", "")
        url = f"https://raw.githubusercontent.com/balancer/backend/refs/heads/v3-main/config/{config_file}"

        # The config/ directory also holds helper modules (e.g. worker-jobs.ts,
        # types.ts, chain-id-to-chain.ts) that aren't network configs and have no
        # `export default` literal. Skip those; only network configs are parseable.
        raw = requests.get(url).text
        if "export default" not in raw:
            continue

        try:
            # Should not raise any exceptions
            config = ts_config_loader(url)
            assert isinstance(
                config, dict
            ), f"Config for {chain} should be a dictionary"
            loaded_any = True
        except Exception as e:
            failed_configs.append((chain, str(e)))

    assert loaded_any, "No network configs were loaded"

    assert (
        len(failed_configs) == 0
    ), f"Failed to load {len(failed_configs)} configs: {failed_configs}"
