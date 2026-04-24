"""Filesystem plugin."""
from ai_contained.plugins.filesystem.fs_write import register as _register_fs_write
from ai_contained.plugins.filesystem.fs_read import register as _register_fs_read
from ai_contained.plugins.filesystem.fs_glob import register as _register_fs_glob
from ai_contained.plugins.filesystem.execute_bash import register as _register_execute_bash


def register(mcp):
    _register_fs_write(mcp)
    _register_fs_read(mcp)
    _register_fs_glob(mcp)
    _register_execute_bash(mcp)
