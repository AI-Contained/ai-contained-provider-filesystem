"""Filesystem provider."""

from fastmcp import FastMCP

from ai_contained.provider.filesystem.fs_glob import register as _register_fs_glob
from ai_contained.provider.filesystem.fs_read import register as _register_fs_read
from ai_contained.provider.filesystem.fs_write import register as _register_fs_write


async def register(mcp: FastMCP) -> None:
    """Register filesystem tools with the MCP server."""
    await _register_fs_write(mcp)
    await _register_fs_read(mcp)
    await _register_fs_glob(mcp)
