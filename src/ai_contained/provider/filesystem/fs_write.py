"""fs_write tool — create, append, str_replace, or insert content in files."""
import os
from typing import Literal

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def fs_write(
        command: Literal["create", "append", "str_replace", "insert"],
        path: str,
        ctx: Context,
        file_text: str = "",
        new_str: str = "",
        old_str: str = "",
        insert_line: int = 0,
        summary: str = "",
    ) -> str:
        """Create, append to, or edit a file.

        Parameters
        ----------
          command      (required) One of: "create", "append", "str_replace", "insert"
          path         (required) Absolute or relative file path. Parent directories
                       are created automatically for "create". Must exist for all other commands.
          file_text    (create only) Full file content to write. Omit or pass "" for empty file.
          new_str      (append, str_replace, insert) Content to add or use as replacement.
                       For insert: MUST include a trailing newline (e.g. "text\\n") — inserted
                       text is joined directly to the adjacent line without a separator.
          old_str      (str_replace only) Exact text to find and replace. Must match exactly
                       once — include enough surrounding context to ensure uniqueness.
                       To delete a line, include its trailing newline in old_str and set new_str="".
          insert_line  (insert only) 1-based line number to insert after. 0 = before first line.
                       Values beyond EOF append to end. Line numbers in the diff preview may be
                       off-by-one when inserting beyond EOF (known display bug — file content is correct).
          summary      (optional, all commands) Human-readable description of the change shown
                       to the user in the confirmation prompt. Always provide this.

        Return value:
          "" on success. On error, returns a descriptive message (is_error=True):
          - "Failed to validate tool parameters: ..." — path does not exist (append/str_replace/insert)
          - "no occurrences of \\"<old_str>\\" were found" — str_replace match not found
          - "N occurrences of old_str were found when only 1 is expected" — str_replace not unique

        Gotchas:
          - append to empty file produces a spurious leading newline in the file content
          - create always overwrites — use str_replace for targeted edits
          - str_replace with new_str="" strips one trailing newline from the result

        Examples
        --------
          # Create a new file
          {"command": "create", "path": "/src/hello.py", "file_text": "print('hello')\n", "summary": "Add hello script"}

          # Replace unique text
          {"command": "str_replace", "path": "/src/hello.py", "old_str": "print('hello')", "new_str": "print('world')", "summary": "Update greeting"}

          # Delete a line (include trailing newline in old_str)
          {"command": "str_replace", "path": "/src/hello.py", "old_str": "print('world')\n", "new_str": "", "summary": "Remove print"}

          # Insert after line 3 (always include trailing newline in new_str)
          {"command": "insert", "path": "/src/hello.py", "insert_line": 3, "new_str": "# inserted\n", "summary": "Add comment"}

          # Append to file
          {"command": "append", "path": "/src/hello.py", "new_str": "# end of file\n", "summary": "Add footer"}

        """

        def _colorize(line: str) -> str:
            if os.environ.get("COLOR", "ascii") != "ascii":
                return line
            if line.startswith("-"):
                return f"\033[31m{line}\033[0m"
            if line.startswith("+"):
                return f"\033[32m{line}\033[0m"
            return line

        def _elicit_msg(header: str, diff: str) -> str:
            purpose = f"\nPurpose: {summary}" if summary else ""
            return (
                f"{header}{purpose}\n\n"
                f"{diff}\n\n\n"
                "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
            )

        def _unified_diff(old_lines: list[str], new_lines: list[str], show_all_context: bool = False, insert_line: int | None = None) -> str:
            import difflib
            matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
            opcodes = list(matcher.get_opcodes())
            # classify: does the diff have changes at start, middle, or end?
            change_indices = [i for i, (t,_,_,_,_) in enumerate(opcodes) if t != "equal"]
            has_leading_equal = opcodes[0][0] == "equal" if opcodes else False
            has_trailing_equal = opcodes[-1][0] == "equal" if opcodes else False
            out = []
            for idx, (tag, i1, i2, j1, j2) in enumerate(opcodes):
                if tag == "equal":
                    prev_change = idx > 0 and opcodes[idx-1][0] != "equal"
                    next_change = idx < len(opcodes)-1 and opcodes[idx+1][0] != "equal"
                    if not show_all_context and not (prev_change and next_change):
                        continue
                    lines_range = list(range(i1, i2))
                    if show_all_context:
                        is_leading = not prev_change
                        is_trailing = not next_change
                        if is_leading:
                            lines_range = lines_range[1:] if len(lines_range) > 2 else lines_range
                        elif is_trailing:
                            lines_range = lines_range[:2]   # show first 2 lines only
                    for k in lines_range:
                        out.append(_colorize(f"  {k+1}, {j1+(k-i1)+1}: {old_lines[k]}"))
                elif tag in ("replace", "delete"):
                    for k, line in enumerate(old_lines[i1:i2]):
                        out.append(_colorize(f"- {i1+k+1}   : {line}"))
                    if tag == "replace":
                        for k, line in enumerate(new_lines[j1:j2]):
                            out.append(_colorize(f"+    {j1+k+1}: {line}"))
                elif tag == "insert":
                    for k, line in enumerate(new_lines[j1:j2]):
                        out.append(_colorize(f"+    {j1+k+1}: {line}"))
            return "\n".join(out)

        async def _elicit(header: str, diff: str) -> None:
            result = await ctx.elicit(message=_elicit_msg(header, diff), response_type=None)
            if result.action != "accept":
                raise ToolError("Tool use was cancelled by the user")

        if command == "create":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            old_content = open(path).read() if os.path.exists(path) else None
            new_lines = file_text.splitlines()
            if old_content is None:
                diff = "\n".join(_colorize(f"+    {i+1}: {l}") for i, l in enumerate(new_lines))
            else:
                diff = _unified_diff(old_content.splitlines(), new_lines)
            header = f"I'll create the following file: {path} (using tool: write)"
            await _elicit(header, diff)
            with open(path, "w") as f:
                f.write(file_text)

        elif command == "append":
            if not os.path.exists(path):
                raise ToolError("Failed to validate tool parameters: The provided path must exist in order to replace or insert contents into it")
            old_content = open(path).read()
            needs_newline = not old_content.endswith("\n")
            appended = ("\n" if needs_newline else "") + new_str
            new_content = old_content + appended
            old_lines = old_content.splitlines()
            new_lines = new_content.splitlines()
            # skip the empty line introduced by the prepended newline on empty files
            added_lines = [l for l in new_lines[len(old_lines):] if l]
            new_line_num = len(old_lines) + (2 if not old_lines else 1)
            diff = "\n".join(_colorize(f"+    {new_line_num + i}: {l}") for i, l in enumerate(added_lines))
            header = f"I'll append content to file: {path} (using tool: write)"
            await _elicit(header, diff)
            with open(path, "w") as f:
                f.write(new_content)

        elif command == "str_replace":
            if not os.path.exists(path):
                raise ToolError("Failed to validate tool parameters: The provided path must exist in order to replace or insert contents into it")
            content = open(path).read()
            count = content.count(old_str)
            new_content = content.replace(old_str, new_str, 1)
            if new_str == "" and new_content.endswith("\n"):
                new_content = new_content[:-1]
            if count == 0:
                diff = f"{_colorize(f'- 0   : {old_str}')}\n{_colorize(f'+    0: {new_str}')}"
            else:
                diff = _unified_diff(content.splitlines(), new_content.splitlines())
            header = f"I'll modify the following file: {path} (using tool: write)"
            await _elicit(header, diff)
            if count == 0:
                raise ToolError(f'no occurrences of "{old_str}" were found')
            if count > 1:
                raise ToolError(f"{count} occurrences of old_str were found when only 1 is expected")
            with open(path, "w") as f:
                f.write(new_content)

        elif command == "insert":
            if not os.path.exists(path):
                raise ToolError("Failed to validate tool parameters: The provided path must exist in order to replace or insert contents into it")
            content = open(path).read()
            lines = content.splitlines(keepends=True)
            pos = min(insert_line, len(lines))
            lines.insert(pos, new_str)
            new_content = "".join(lines)
            diff = _unified_diff(content.splitlines(), new_content.splitlines(), show_all_context=True, insert_line=insert_line)
            header = f"I'll insert content into file: {path} (using tool: write)"
            await _elicit(header, diff)
            with open(path, "w") as f:
                f.write(new_content)

        return ""
