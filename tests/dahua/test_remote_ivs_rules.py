"""NVR IVS writes preserve the complete channel table and stable rule IDs."""

from unittest.mock import AsyncMock

import pytest

from custom_components.dahua.client import flatten_rpc2_config
from custom_components.dahua.ivs import ivs_rules_for_channel
from custom_components.dahua.rpc2 import DahuaRpc2Client


def rule(rule_id, enabled, name="IVS-1"):
    return {
        "Id": rule_id, "Class": "Normal", "Name": name,
        "Type": "CrossLineDetection", "Enable": enabled,
        "Points": [{"X": 12, "Y": 34}],
    }


async def test_remote_write_resolves_id_in_fresh_table_and_preserves_other_rules():
    rpc = object.__new__(DahuaRpc2Client)
    current = [rule(2, True, "IVS-2"), rule(1, True)]
    rpc.async_get_remote_ivs_rules = AsyncMock(return_value=current)
    rpc.request = AsyncMock(return_value={"result": True})

    await rpc.async_set_remote_ivs_rule_by_id(10, "1", False)

    rpc.async_get_remote_ivs_rules.assert_awaited_once_with(10)
    rpc.request.assert_awaited_once_with(
        method="configManager.setConfig",
        params={
            "name": "RemoteVideoAnalyseRule",
            "table": [current[0], {**current[1], "Enable": False}],
            "options": [], "channel": 10,
        },
    )
    assert current[1]["Enable"] is True
    assert current[0]["Points"] == [{"X": 12, "Y": 34}]


@pytest.mark.parametrize("table", [[], [rule(2, True)], [rule(1, True), rule(1, False)]])
async def test_missing_or_ambiguous_remote_rule_never_writes(table):
    rpc = object.__new__(DahuaRpc2Client)
    rpc.async_get_remote_ivs_rules = AsyncMock(return_value=table)
    rpc.request = AsyncMock()
    with pytest.raises(ValueError):
        await rpc.async_set_remote_ivs_rule_by_id(10, "1", False)
    rpc.request.assert_not_awaited()


def test_remote_discovery_uses_zero_based_channel_and_normal_class():
    table = flatten_rpc2_config(
        "RemoteVideoAnalyseRule", [rule(1, True), rule(2, False, "IVS-2")],
        "table.RemoteVideoAnalyseRule[10]",
    )
    assert [r["id"] for r in ivs_rules_for_channel(table, 10, "RemoteVideoAnalyseRule")] == ["1", "2"]
    assert ivs_rules_for_channel(table, 11, "RemoteVideoAnalyseRule") == []
