from assertpy import assert_that
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport

from ai_contained.core.mcp.testing import Elicitor


def describe_adventure_recap() -> None:
    PROMPT_NAME = "adventure_recap"

    async def it_registers_the_prompt(client: Client[FastMCPTransport]) -> None:
        prompts = await client.list_prompts()
        assert_that([p.name for p in prompts]).contains(PROMPT_NAME)

    async def it_reflects_stats_after_win(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        elicitor.accept({"value": "go left"}).accept({"value": "open chest"})
        await client.call_tool("play_adventure", {})
        result = await client.get_prompt(PROMPT_NAME, {})
        text = result.messages[0].content.text
        assert_that(text).contains("adventure://stats")

    async def it_reflects_stats_after_loss(client: Client[FastMCPTransport], elicitor: Elicitor) -> None:
        elicitor.accept({"value": "go right"}).accept({"value": "jump across"})
        await client.call_tool("play_adventure", {})
        result = await client.get_prompt(PROMPT_NAME, {})
        text = result.messages[0].content.text
        assert_that(text).contains("adventure://stats")
