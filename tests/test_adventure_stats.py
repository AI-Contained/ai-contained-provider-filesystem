import json

from assertpy import assert_that
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport

from ai_contained.core.mcp.testing import Elicitor


def describe_adventure_stats() -> None:
    STATS_URI = "adventure://stats"

    async def it_registers_the_resource(client: Client[FastMCPTransport]) -> None:
        resources = await client.list_resources()
        assert_that([str(r.uri) for r in resources]).contains(STATS_URI)

    async def it_returns_default_stats(client: Client[FastMCPTransport]) -> None:
        content = await client.read_resource(STATS_URI)
        assert_that(json.loads(content[0].text)).is_equal_to({"health": 100, "adventures": 0})

    async def it_updates_stats_on_win(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        elicitor.accept({"value": "go left"}).accept({"value": "open chest"})
        await client.call_tool("play_adventure", {})
        content = await client.read_resource(STATS_URI)
        assert_that(json.loads(content[0].text)).is_equal_to({"health": 100, "adventures": 1})

    async def it_updates_stats_on_loss(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        elicitor.accept({"value": "go right"}).accept({"value": "jump across"})
        await client.call_tool("play_adventure", {})
        content = await client.read_resource(STATS_URI)
        assert_that(json.loads(content[0].text)).is_equal_to({"health": 90, "adventures": 1})

    async def it_increments_adventures_across_plays(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        num_plays = 2
        for _ in range(num_plays):
            elicitor.accept({"value": "go left"}).accept({"value": "open chest"})
        for _ in range(num_plays):
            await client.call_tool("play_adventure", {})
        content = await client.read_resource(STATS_URI)
        assert_that(json.loads(content[0].text)).contains_entry({"adventures": num_plays})

    async def it_caps_health_at_100_on_win(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        num_plays = 2
        for _ in range(num_plays):
            elicitor.accept({"value": "go left"}).accept({"value": "open chest"})
        for _ in range(num_plays):
            await client.call_tool("play_adventure", {})
        content = await client.read_resource(STATS_URI)
        assert_that(json.loads(content[0].text)).contains_entry({"health": 100})

    async def it_floors_health_at_0_on_loss(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        num_attempts = 11
        for _ in range(num_attempts):
            elicitor.accept({"value": "go right"}).accept({"value": "jump across"})
        for _ in range(num_attempts):
            await client.call_tool("play_adventure", {})
        content = await client.read_resource(STATS_URI)
        assert_that(json.loads(content[0].text)).contains_entry({"health": 0})

    async def it_includes_stats_uri_in_result(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        elicitor.accept({"value": "go left"}).accept({"value": "open chest"})
        result = await client.call_tool("play_adventure", {})
        assert_that(result.data).contains("adventure://stats")
