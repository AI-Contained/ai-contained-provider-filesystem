"""fs_read tool — read files, directories, and search for patterns."""

import json
import os
import stat
from datetime import datetime
from typing import Annotated, Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field


class LineOperation(BaseModel):
    """Parameters for a line-range read operation."""

    mode: Literal["Line"]
    path: str
    start_line: int | None = None
    end_line: int | None = None


class SearchOperation(BaseModel):
    """Parameters for a pattern search operation."""

    mode: Literal["Search"]
    path: str
    pattern: str
    context_lines: int = 2


class DirectoryOperation(BaseModel):
    """Parameters for a directory listing operation."""

    mode: Literal["Directory"]
    path: str
    depth: int = 0
    max_entries: int = 1000
    offset: int = 0
    exclude_patterns: list[str] = ["node_modules", ".git", "dist", "build", "out", ".cache", "target"]


Operation = Annotated[LineOperation | SearchOperation | DirectoryOperation, Field(discriminator="mode")]


def register(mcp: FastMCP) -> None:
    """Register the fs_read tool with the MCP server."""

    @mcp.tool()
    async def fs_read(operations: list[Operation], ctx: Context) -> str:
        """Read files, directories, and images with support for line ranges, pattern search, and batch operations.

        Parameters
        ----------
          operations  (required) List of one or more operation objects. All operations are
                      validated before any elicitation is shown — if any path is invalid,
                      the entire call fails with no elicitation fired.

        Operation types (discriminated by "mode"):

          Line mode:
            mode        "Line" (required)
            path        File path (required). Must exist.
            start_line  1-based start line (optional, default: 1). Negative values count
                        from end (-1 = last line). 0 is invalid.
            end_line    1-based end line (optional, default: last line). Values beyond EOF
                        are clamped silently. If start_line > end_line, returns end_line only.

          Search mode:
            mode          "Search" (required)
            path          File path (required). Must exist.
            pattern       Search string (required). Case-insensitive. Literal match — NOT regex.
            context_lines Lines of context around each match (optional, default: 2).
                          Set to 0 to suppress context.

          Directory mode:
            mode             "Directory" (required)
            path             Directory path (required). Must exist.
            depth            Max recursion depth (optional, default: 0 = non-recursive).
            max_entries      Max entries to return (optional, default: 1000).
            offset           Skip first N entries for pagination (optional, default: 0).
            exclude_patterns Glob patterns to exclude (optional, default: common build/cache dirs).

        Return value:
          Single operation: raw result string (file content, JSON search results, or directory listing).
          Batch operations: results separated by "=== Operation N Result (Text) ===" headers.

        Error cases (is_error=True, no elicitation fired):
          - "Failed to validate tool parameters: '<path>' does not exist" — file/dir not found
          - "starting index: N is outside of the allowed range: (-M, M)" — line index out of bounds

        Gotchas:
          - Search pattern is literal, not regex — "bra.o" will NOT match "bravo"
          - Negative line indices are resolved to absolute line numbers in the elicitation message
          - Reading an empty file returns "" without error
          - Batch: one invalid operation fails the entire call — no partial results

        Examples
        --------
          # Read entire file
          {"operations": [{"mode": "Line", "path": "/src/main.py"}]}

          # Read lines 10-20
          {"operations": [{"mode": "Line", "path": "/src/main.py", "start_line": 10, "end_line": 20}]}

          # Search with no surrounding context
          {"operations": [{"mode": "Search", "path": "/src/main.py", "pattern": "TODO", "context_lines": 0}]}

          # List directory recursively
          {"operations": [{"mode": "Directory", "path": "/src", "depth": 2}]}

          # Batch: read two files in one call
          {"operations": [{"mode": "Line", "path": "/src/a.py"}, {"mode": "Line", "path": "/src/b.py"}]}

        """

        def _validate(op: Operation) -> None:
            if isinstance(op, (LineOperation, SearchOperation)) and not os.path.isfile(op.path):
                raise ToolError(f"Failed to validate tool parameters: '{op.path}' does not exist")
            if isinstance(op, DirectoryOperation) and not os.path.isdir(op.path):
                raise ToolError(f"Failed to validate tool parameters: Directory not found: {op.path}")

        def _elicit_msg_single(op: Operation) -> str:
            if isinstance(op, LineOperation):
                start = op.start_line
                end = op.end_line
                if start is None and end is None:
                    return f"Reading file: {op.path}, all lines (using tool: read)"
                # resolve negative/zero for display
                if start is not None and (start <= 0 or end is None or end == -1):
                    n = len(open(op.path).readlines()) if os.path.isfile(op.path) else 0
                    if start == 0:
                        start = n + 1
                    elif start < 0:
                        start = n + start + 1
                if end is None or end == -1:
                    return f"Reading file: {op.path}, from line {start} to end of file (using tool: read)"
                return f"Reading file: {op.path}, from line {start} to {end} (using tool: read)"
            elif isinstance(op, SearchOperation):
                return f"Searching: {op.path} for pattern: {op.pattern.lower()} (using tool: read)"
            elif isinstance(op, DirectoryOperation):
                return f"Reading directory: {op.path} (using tool: read, max depth: {op.depth}, max entries: {op.max_entries}, excluding: defaults)"

        def _elicit_msg(ops: list[Operation]) -> str:
            if len(ops) == 1:
                return _elicit_msg_single(ops[0])
            lines = [f"Batch fs_read operation with {len(ops)} operations (using tool: read)", ""]
            for i, op in enumerate(ops, 1):
                if isinstance(op, LineOperation):
                    if op.start_line is None and op.end_line is None:
                        detail = f"Reading file: {op.path}, all lines"
                    elif op.end_line is None or op.end_line == -1:
                        detail = f"Reading file: {op.path}, from line {op.start_line} to end of file"
                    else:
                        detail = f"Reading file: {op.path}, from line {op.start_line} to {op.end_line}"
                elif isinstance(op, SearchOperation):
                    detail = f"Searching: {op.path} for pattern: {op.pattern.lower()}"
                elif isinstance(op, DirectoryOperation):
                    detail = f"Reading directory: {op.path}"
                lines.append(f"↱ Operation {i}: {detail}")
            return "\n".join(lines)

        def _read_line(op: LineOperation) -> str:
            lines = open(op.path).read().splitlines(keepends=True)
            n = len(lines)
            start = op.start_line if op.start_line is not None else 1
            end = op.end_line if op.end_line is not None else n

            # empty file
            if n == 0:
                return ""

            if start == 0:
                raise ToolError(f"starting index: 0 is outside of the allowed range: (-{n}, {n})")
            if abs(start) > n:
                raise ToolError(f"starting index: {start} is outside of the allowed range: (-{n}, {n})")

            if start < 0:
                start = n + start + 1
            if end < 0:
                end = n + end + 1

            end = min(end, n)
            if start > end:
                start = end

            selected = lines[start - 1 : end]
            result = "".join(selected)
            # strip trailing newline for partial reads (not when reading to actual EOF)
            reading_to_eof = op.end_line is None or op.end_line < 0 or end >= n
            reading_from_start = op.start_line is None or op.start_line == 1
            if not (reading_from_start and reading_to_eof):
                result = result.rstrip("\n")
            return result

        def _search(op: SearchOperation) -> str:
            lines = open(op.path).readlines()
            results = []
            for i, line in enumerate(lines):
                if op.pattern.lower() in line.lower():
                    ctx_start = max(0, i - op.context_lines)
                    ctx_end = min(len(lines), i + op.context_lines + 1)
                    context = ""
                    for j in range(ctx_start, ctx_end):
                        prefix = "→" if j == i else " "
                        context += f"{prefix} {j + 1}: {lines[j].rstrip(chr(10))}\n"
                    results.append({"line_number": i + 1, "context": context})
            return json.dumps(results, separators=(",", ":"), ensure_ascii=False)

        def _directory(op: DirectoryOperation) -> str:
            entries = []
            for root, dirs, files in os.walk(op.path):
                level = root.replace(op.path, "").count(os.sep)
                if level > op.depth:
                    dirs.clear()
                    continue
                dirs[:] = [d for d in dirs if d not in op.exclude_patterns]
                for name in dirs:
                    entries.append(os.path.join(root, name))
                for name in files:
                    entries.append(os.path.join(root, name))

            entries = sorted(entries, key=lambda p: os.path.getmtime(p), reverse=True)[
                op.offset : op.offset + op.max_entries
            ]

            lines = [f"# Total entries: {len(entries)}", ""]
            for entry in entries:
                s = os.stat(entry)
                mode_str = stat.filemode(s.st_mode)
                mtime = datetime.fromtimestamp(s.st_mtime).strftime("%b %d %H:%M")
                lines.append(f"{mode_str} {s.st_nlink} {s.st_uid} {s.st_gid} {s.st_size} {mtime} {entry}")
            return "\n".join(lines) + "\n"

        def _execute(op: Operation) -> str:
            if isinstance(op, LineOperation):
                return _read_line(op)
            elif isinstance(op, SearchOperation):
                return _search(op)
            elif isinstance(op, DirectoryOperation):
                return _directory(op)

        # validate all ops first
        for op in operations:
            _validate(op)

        # elicit (skipped when EXPERIMENTAL_ALLOW_ALL_READS is set)
        if not os.environ.get("EXPERIMENTAL_ALLOW_ALL_READS"):
            msg = _elicit_msg(operations)
            result = await ctx.elicit(message=msg, response_type=None)
            if result.action != "accept":
                raise ToolError("Tool use was cancelled by the user")

        # execute
        if len(operations) == 1:
            return _execute(operations[0])
        else:
            parts = []
            for i, op in enumerate(operations, 1):
                content = _execute(op).rstrip("\n")
                parts.append(f"=== Operation {i} Result (Text) ===\n{content}\n")
            return "\n".join(parts)
