"""glob tool — find files matching a glob pattern."""

import json
import os
from pathlib import Path

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError


async def register(mcp: FastMCP) -> None:
    """Register the fs_glob tool with the MCP server."""
    # TODO: consider using ctx.info()/ctx.warning() to surface a human-readable summary
    # after returning results. Agent's UI generates these from the JSON result:
    #   ✓ Successfully found 4 files under <path>
    #   ✓ Successfully found 4 files under <path> (result is truncated)
    #   ❗ No files found matching pattern: <pattern> under <path>

    @mcp.tool(name="fs_glob")
    async def fs_glob(
        pattern: str,
        ctx: Context,
        path: str | None = None,
        max_depth: int | None = None,
        limit: int | None = None,
    ) -> str:
        """Find files matching a glob pattern, respecting directory depth and result limits.

        Parameters
        ----------
          pattern    Glob pattern (required). Supports * (any chars), ** (any chars, same
                     as *), and ? (single char). Regex quantifiers (e.g. +) are NOT
                     supported. Examples: "**/*.py", "*.txt", "src/**/*.ts"
          path       Root directory to search from (optional, default: cwd).
                     If the path does not exist, elicitation still fires and the result
                     is a JSON error object (not a tool error).
          max_depth  Maximum directory depth to traverse (optional).
                     depth=0 returns nothing (not even root-level files).
                     depth=1 returns root-level files only.
                     depth=2 returns root + one level of subdirectories, etc.
                     NOTE: * and ** behave identically — depth is controlled by max_depth,
                     not the pattern.
          limit      Maximum number of files to return (optional).
                     totalFiles always reflects the full match count before truncation.
                     limit=0 returns empty filePaths with truncated=true.

        Return value (JSON):
          On matches:
            { "filePaths": [...], "totalFiles": N, "truncated": true|false }
          On no matches:
            { "filePaths": [], "message": "No files found matching pattern: <pattern>", "totalFiles": 0, "truncated": false }
          On nonexistent path (after elicitation):
            { "error": "Path does not exist: <path>" }

        Error cases (is_error=True, no elicitation fired):
          - pattern is empty: "Failed to validate tool parameters: Glob pattern cannot be empty"

        Gotchas:
          - Elicitation fires even for nonexistent paths — the error is in the JSON result, not a tool error
          - totalFiles reflects the depth-constrained count, not the global file count
          - truncated=false when limit >= totalFiles (no files are cut off)
          - File order is not guaranteed to be alphabetical

        """
        if not pattern:
            raise ToolError("Failed to validate tool parameters: Glob pattern cannot be empty")

        root = path or os.getcwd()

        # elicit (skipped when EXPERIMENTAL_ALLOW_ALL_READS is set)
        if not os.environ.get("EXPERIMENTAL_APPROVE_ALL_READS"):
            msg = f"Searching for files: {pattern} in {root} (using tool: glob)"
            result = await ctx.elicit(message=msg, response_type=None)
            if result.action != "accept":
                raise ToolError("Tool use was cancelled by the user")

        if not os.path.isdir(root):
            return json.dumps({"error": f"Path does not exist: {root}"})

        matches = []
        for dirpath, dirnames, filenames in os.walk(root):
            rel = os.path.relpath(dirpath, root)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if max_depth is not None and depth >= max_depth:
                dirnames.clear()
                continue
            for name in filenames:
                full = os.path.join(dirpath, name)
                if Path(full).match(pattern):
                    matches.append(full)

        total = len(matches)

        if limit is not None:
            truncated = len(matches) > limit
            matches = matches[:limit]
        else:
            truncated = False

        if total == 0:
            return json.dumps(
                {
                    "filePaths": [],
                    "message": f"No files found matching pattern: {pattern}",
                    "totalFiles": 0,
                    "truncated": False,
                }
            )

        return json.dumps({"filePaths": matches, "totalFiles": total, "truncated": truncated})
