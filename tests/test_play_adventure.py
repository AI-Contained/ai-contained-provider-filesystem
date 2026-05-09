import pytest
from assertpy import assert_that
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport

from ai_contained.core.mcp.testing import Elicitor


def describe_play_adventure() -> None:
    async def it_registers_the_tool(client: Client[FastMCPTransport]) -> None:
        tools = await client.list_tools()
        assert_that([t.name for t in tools]).contains("play_adventure")

    async def it_wins_via_cave(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        elicitor.accept({"value": "go left"}).accept({"value": "open chest"})
        result = await client.call_tool("play_adventure", {})
        assert_that(result.data).contains("You win")

    async def it_wins_via_river_boat(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        elicitor.accept({"value": "go right"}).accept({"value": "take boat"})
        result = await client.call_tool("play_adventure", {})
        assert_that(result.data).contains("You win")

    async def it_loses_by_jumping(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        elicitor.accept({"value": "go right"}).accept({"value": "jump across"})
        result = await client.call_tool("play_adventure", {})
        assert_that(result.data).contains("Game over")

    async def it_can_go_back_from_cave(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        elicitor.accept({"value": "go left"}).accept({"value": "go back"}).accept({"value": "go right"}).accept(
            {"value": "take boat"}
        )
        result = await client.call_tool("play_adventure", {})
        assert_that(result.data).contains("You win")

    async def it_abandons_on_decline(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        elicitor.decline()
        result = await client.call_tool("play_adventure", {})
        assert_that(result.data).contains("abandoned")

    @pytest.mark.parametrize("method", ["decline", "cancel"])
    async def it_abandons_on_non_accept(client: Client[FastMCPTransport], elicitor: Elicitor, method: str) -> None:
        getattr(elicitor, method)()
        result = await client.call_tool("play_adventure", {})
        assert_that(result.data).contains("abandoned")
