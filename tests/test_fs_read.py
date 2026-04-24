import pytest
from assertpy import assert_that
from fastmcp.client import Client

from conftest import make_capture_handler


@pytest.fixture(autouse=True)
def expected(sandbox):
    value = "alpha\nbravo\ncharlie\nbravo\ndelta\n"
    subject = sandbox / "test_subject.txt"
    subject.write_text(value)
    return {"subject": str(subject), "value": value}


def describe_fs_read():

    def describe_line_mode():
        async def it_reads_entire_file(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": expected["subject"]}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Reading file: {expected["subject"]}, all lines (using tool: read)")
                assert_that(result.content[0].text).is_equal_to("alpha\nbravo\ncharlie\nbravo\ndelta\n")

        async def it_reads_a_line_range(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": expected["subject"], "start_line": 2, "end_line": 4}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Reading file: {expected["subject"]}, from line 2 to 4 (using tool: read)")
                assert_that(result.content[0].text).is_equal_to("bravo\ncharlie\nbravo")

        async def it_reads_using_negative_line_index(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": expected["subject"], "start_line": -2, "end_line": -1}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Reading file: {expected["subject"]}, from line 4 to end of file (using tool: read)")
                assert_that(result.content[0].text).is_equal_to("bravo\ndelta")

        async def it_reads_single_line(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": expected["subject"], "start_line": 1, "end_line": 1}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Reading file: {expected["subject"]}, from line 1 to 1 (using tool: read)")
                assert_that(result.content[0].text).is_equal_to("alpha")

        async def it_clamps_end_line_beyond_eof(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": expected["subject"], "start_line": 1, "end_line": 999}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Reading file: {expected["subject"]}, from line 1 to 999 (using tool: read)")
                assert_that(result.content[0].text).is_equal_to("alpha\nbravo\ncharlie\nbravo\ndelta\n")

        async def it_returns_end_line_when_start_greater_than_end(mcp, expected):
            # NOTE: no error — returns content at end_line only
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": expected["subject"], "start_line": 4, "end_line": 2}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Reading file: {expected["subject"]}, from line 4 to 2 (using tool: read)")
                assert_that(result.content[0].text).is_equal_to("bravo")

        async def it_errors_on_start_line_beyond_eof(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": expected["subject"], "start_line": 999}]}, raise_on_error=False)
                assert_that(result.is_error).is_true()
                assert_that(h.messages[0]).is_equal_to(f"Reading file: {expected["subject"]}, from line 999 to end of file (using tool: read)")
                assert_that(result.content[0].text).is_equal_to("starting index: 999 is outside of the allowed range: (-5, 5)")

        async def it_errors_on_line_zero(mcp, expected):
            # NOTE: line indexing is 1-based — 0 is invalid. Elicitation shows "from line 6" (one past EOF)
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": expected["subject"], "start_line": 0}]}, raise_on_error=False)
                assert_that(result.is_error).is_true()
                assert_that(h.messages[0]).is_equal_to(f"Reading file: {expected["subject"]}, from line 6 to end of file (using tool: read)")
                assert_that(result.content[0].text).is_equal_to("starting index: 0 is outside of the allowed range: (-5, 5)")

        async def it_reads_empty_file(mcp, tmp_path):
            path = str(tmp_path / "empty.txt")
            open(path, "w").close()
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": path}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Reading file: {path}, all lines (using tool: read)")
                assert_that(result.content[0].text).is_equal_to("")

        async def it_errors_on_nonexistent_file(mcp, expected):
            # NOTE: validation fires before tool runs — no elicitation message
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": "/code/volatile/ghost.txt"}]}, raise_on_error=False)
                assert_that(result.is_error).is_true()
                assert_that(h.messages).is_empty()
                assert_that(result.content[0].text).is_equal_to("Failed to validate tool parameters: '/code/volatile/ghost.txt' does not exist")

    def describe_search_mode():
        async def it_finds_matching_lines(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Search", "path": expected["subject"], "pattern": "bravo"}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching: {expected["subject"]} for pattern: bravo (using tool: read)")
                assert_that(result.content[0].text).is_equal_to(
                    '[{"line_number":2,"context":"  1: alpha\\n→ 2: bravo\\n  3: charlie\\n  4: bravo\\n"},'
                    '{"line_number":4,"context":"  2: bravo\\n  3: charlie\\n→ 4: bravo\\n  5: delta\\n"}]'
                )

        async def it_returns_empty_list_when_no_matches(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Search", "path": expected["subject"], "pattern": "nonexistent"}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching: {expected["subject"]} for pattern: nonexistent (using tool: read)")
                assert_that(result.content[0].text).is_equal_to("[]")

        async def it_is_case_insensitive(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Search", "path": expected["subject"], "pattern": "BRAVO"}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching: {expected["subject"]} for pattern: bravo (using tool: read)")
                assert_that(result.content[0].text).is_equal_to(
                    '[{"line_number":2,"context":"  1: alpha\\n→ 2: bravo\\n  3: charlie\\n  4: bravo\\n"},'
                    '{"line_number":4,"context":"  2: bravo\\n  3: charlie\\n→ 4: bravo\\n  5: delta\\n"}]'
                )

        async def it_matches_literally_not_as_regex(mcp, expected):
            # NOTE: "bra.o" does NOT match "bravo" — pattern is literal, not regex
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Search", "path": expected["subject"], "pattern": "bra.o"}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching: {expected["subject"]} for pattern: bra.o (using tool: read)")
                assert_that(result.content[0].text).is_equal_to("[]")

        async def it_respects_context_lines_zero(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"context_lines": 0, "mode": "Search", "path": expected["subject"], "pattern": "bravo"}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching: {expected["subject"]} for pattern: bravo (using tool: read)")
                assert_that(result.content[0].text).is_equal_to(
                    '[{"line_number":2,"context":"→ 2: bravo\\n"},'
                    '{"line_number":4,"context":"→ 4: bravo\\n"}]'
                )

    def describe_directory_mode():
        async def it_lists_directory_entries(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Directory", "path": "/code/volatile/dirtest"}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to("Reading directory: /code/volatile/dirtest (using tool: read, max depth: 0, max entries: 1000, excluding: defaults)")
                assert_that(result.content[0].text).is_equal_to(
                    "# Total entries: 2\n\n"
                    "-rw-r--r-- 1 1000 1000 2 Apr 22 07:30 /code/volatile/dirtest/b.txt\n"
                    "-rw-r--r-- 1 1000 1000 2 Apr 22 07:29 /code/volatile/dirtest/a.txt\n"
                )

        async def it_lists_recursively_with_depth(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"depth": 1, "mode": "Directory", "path": "/code/volatile/dirtest"}]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to("Reading directory: /code/volatile/dirtest (using tool: read, max depth: 1, max entries: 1000, excluding: defaults)")
                assert_that(result.content[0].text).is_equal_to(
                    "# Total entries: 2\n\n"
                    "-rw-r--r-- 1 1000 1000 2 Apr 22 07:30 /code/volatile/dirtest/b.txt\n"
                    "-rw-r--r-- 1 1000 1000 2 Apr 22 07:29 /code/volatile/dirtest/a.txt\n"
                )

        async def it_errors_on_nonexistent_directory(mcp, expected):
            # NOTE: validation fires before tool runs — no elicitation message
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": "/code/volatile/no_such_dir/file.txt"}]}, raise_on_error=False)
                assert_that(result.is_error).is_true()
                assert_that(h.messages).is_empty()
                assert_that(result.content[0].text).is_equal_to("Failed to validate tool parameters: '/code/volatile/no_such_dir/file.txt' does not exist")

    def describe_batch_operations():
        async def it_reads_multiple_files_in_one_call(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [
                    {"mode": "Line", "path": "/code/volatile/dirtest/a.txt"},
                    {"mode": "Line", "path": "/code/volatile/dirtest/b.txt"},
                ]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(
                    "Batch fs_read operation with 2 operations (using tool: read)\n\n"
                    "↱ Operation 1: Reading file: /code/volatile/dirtest/a.txt, all lines\n"
                    "↱ Operation 2: Reading file: /code/volatile/dirtest/b.txt, all lines"
                )
                assert_that(result.content[0].text).is_equal_to(
                    "=== Operation 1 Result (Text) ===\nx\n\n"
                    "=== Operation 2 Result (Text) ===\nx\n"
                )

        async def it_fails_entire_batch_if_one_operation_is_invalid(mcp, expected):
            # NOTE: one invalid path fails the whole call — no partial results, no elicitation
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [
                    {"mode": "Line", "path": expected["subject"]},
                    {"mode": "Line", "path": "/code/volatile/ghost.txt"},
                ]}, raise_on_error=False)
                assert_that(result.is_error).is_true()
                assert_that(h.messages).is_empty()
                assert_that(result.content[0].text).is_equal_to("Failed to validate tool parameters: '/code/volatile/ghost.txt' does not exist")

    def describe_decline():
        async def it_returns_cancelled_when_user_declines(mcp, expected):
            from conftest import make_decline_handler
            h = make_decline_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_read", {"operations": [{"mode": "Line", "path": expected["subject"]}]}, raise_on_error=False)
                assert_that(result.is_error).is_true()
                assert_that(result.content[0].text).is_equal_to("Tool use was cancelled by the user")
