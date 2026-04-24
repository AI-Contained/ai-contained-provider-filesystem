"""Filesystem provider."""
from ai_contained.provider.filesystem.fs_write import register as _register_fs_write
from ai_contained.provider.filesystem.fs_read import register as _register_fs_read
from ai_contained.provider.filesystem.fs_glob import register as _register_fs_glob


def register(mcp):
    _register_fs_write(mcp)
    _register_fs_read(mcp)
    _register_fs_glob(mcp)
