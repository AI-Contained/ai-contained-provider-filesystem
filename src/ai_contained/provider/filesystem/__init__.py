"""Filesystem provider."""

from ai_contained.core.mcp import ProviderContext
from ai_contained.provider.filesystem.fs_glob import register as _register_fs_glob
from ai_contained.provider.filesystem.fs_read import register as _register_fs_read
from ai_contained.provider.filesystem.fs_write import register as _register_fs_write


async def provide(ctx: ProviderContext) -> None:
    """Register filesystem tools with the MCP server."""
    await _register_fs_write(ctx)
    await _register_fs_read(ctx)
    await _register_fs_glob(ctx)
