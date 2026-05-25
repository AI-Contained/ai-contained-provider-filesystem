import pytest
from assertpy import assert_that
from conftest import make_capture_handler
from fastmcp.client import Client


@pytest.fixture(autouse=True)
def expected(sandbox):
    value = "alpha\nbravo\ncharlie\nbravo\ndelta\n"
    subject = sandbox / "test_subject.txt"
    subject.write_text(value)
    return {"subject": str(subject), "value": value}


def describe_fs_write():

    def describe_create():
        async def it_creates_a_new_file(mcp, tmp_path):
            path = str(tmp_path / "new.txt")
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_write", {"command": "create", "path": path, "file_text": "hello"})
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll create the following file: {path} (using tool: write)\n\n"
                    "+    1: hello\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                assert_that(open(path).read()).is_equal_to("hello")

        async def it_overwrites_existing_file(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write", {"command": "create", "path": expected["subject"], "file_text": "replaced"}
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll create the following file: {expected['subject']} (using tool: write)\n\n"
                    "- 1   : alpha\n"
                    "- 2   : bravo\n"
                    "- 3   : charlie\n"
                    "- 4   : bravo\n"
                    "- 5   : delta\n"
                    "+    1: replaced\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                assert_that(open(expected["subject"]).read()).is_equal_to("replaced")

        async def it_creates_with_empty_file_text(mcp, tmp_path):
            path = str(tmp_path / "empty.txt")
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_write", {"command": "create", "path": path, "file_text": ""})
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll create the following file: {path} (using tool: write)\n\n\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                assert_that(open(path).read()).is_equal_to("")

        async def it_creates_missing_parent_directories(mcp, tmp_path):
            path = str(tmp_path / "a" / "b" / "c.txt")
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_write", {"command": "create", "path": path, "file_text": "hello"})
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll create the following file: {path} (using tool: write)\n\n"
                    "+    1: hello\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                assert_that(open(path).read()).is_equal_to("hello")

        async def it_create_with_identical_content_is_noop(mcp, tmp_path):
            # BUG CANDIDATE: creating a file with identical content still shows a diff and says "Replacing"
            # Expected: no elicitation fired (no changes), or elicitation message says "Creating" with no diff
            # Actual (observed): shows "- 1: hello / + 1: hello" diff and "Replacing"
            path = str(tmp_path / "existing.txt")
            open(path, "w").write("hello")
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_write", {"command": "create", "path": path, "file_text": "hello"})
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                # TODO: assert exact elicitation message once confirmed
                assert_that(open(path).read()).is_equal_to("hello")

    def describe_append():
        async def it_appends_to_file(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write", {"command": "append", "path": expected["subject"], "new_str": "echo"}
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll append content to file: {expected['subject']} (using tool: write)\n\n"
                    "+    6: echo\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                assert_that(open(expected["subject"]).read()).is_equal_to("alpha\nbravo\ncharlie\nbravo\ndelta\necho")

        async def it_adds_newline_before_append_if_missing(mcp, expected):
            with open(expected["subject"], "w") as f:
                f.write("no newline")
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write", {"command": "append", "path": expected["subject"], "new_str": "appended"}
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll append content to file: {expected['subject']} (using tool: write)\n\n"
                    "+    2: appended\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                assert_that(open(expected["subject"]).read()).is_equal_to("no newline\nappended")

        async def it_appends_to_empty_file(mcp, expected):
            with open(expected["subject"], "w") as f:
                f.write("")
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write", {"command": "append", "path": expected["subject"], "new_str": "first"}
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll append content to file: {expected['subject']} (using tool: write)\n\n"
                    "+    2: first\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                # NOTE: empty file gets a spurious leading newline — appended content lands on line 2
                assert_that(open(expected["subject"]).read()).is_equal_to("\nfirst")

        async def it_errors_when_new_str_is_missing(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write", {"command": "append", "path": expected["subject"], "file_text": "echo"},
                    raise_on_error=False,
                )
                assert_that(result.is_error).is_true()
                assert_that(result.content[0].text).is_equal_to(
                    "Failed to validate tool parameters: append requires new_str"
                )
                assert_that(h.messages).is_empty()
                assert_that(open(expected["subject"]).read()).is_equal_to(expected["value"])

        async def it_errors_on_nonexistent_file(mcp, tmp_path):
            # NOTE: real CLI crashes with Rust panic — no result returned
            # "Agent is having trouble responding right now: failed to print tool, `fs_write`: No such file or directory"
            # Mock returns a clean error result instead
            path = str(tmp_path / "ghost.txt")
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write", {"command": "append", "path": path, "new_str": "x"}, raise_on_error=False
                )
                assert_that(result.is_error).is_true()
                assert_that(result.content[0].text).is_equal_to(
                    "Failed to validate tool parameters: The provided path must exist in order to replace or insert contents into it"
                )
                assert_that(h.messages).is_empty()

    def describe_str_replace():

        async def it_replaces_unique_occurrence(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "str_replace", "path": expected["subject"], "old_str": "charlie", "new_str": "CHARLIE"},
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll modify the following file: {expected['subject']} (using tool: write)\n\n"
                    "- 3   : charlie\n"
                    "+    3: CHARLIE\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                assert_that(open(expected["subject"]).read()).is_equal_to("alpha\nbravo\nCHARLIE\nbravo\ndelta\n")

        async def it_errors_on_duplicate_occurrence(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "str_replace", "path": expected["subject"], "old_str": "bravo", "new_str": "X"},
                    raise_on_error=False,
                )
                assert_that(result.is_error).is_true()
                assert_that(result.content[0].text).is_equal_to(
                    "2 occurrences of old_str were found when only 1 is expected"
                )
                assert_that(h.messages).is_empty()
                assert_that(open(expected["subject"]).read()).is_equal_to(expected["value"])

        async def it_errors_when_old_str_is_not_found(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {
                        "command": "str_replace",
                        "path": expected["subject"],
                        "old_str": "alpha\nMISSING\ncharlie",
                        "new_str": "alpha\nreplaced\ncharlie",
                    },
                    raise_on_error=False,
                )
                assert_that(result.is_error).is_true()
                assert_that(result.content[0].text).is_equal_to("no occurrences of 'old_str' were found")
                assert_that(h.messages).is_empty()


        async def it_errors_on_nonexistent_file(mcp, tmp_path):
            path = str(tmp_path / "ghost.txt")
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "str_replace", "path": path, "old_str": "x", "new_str": "y"},
                    raise_on_error=False,
                )
                assert_that(result.is_error).is_true()
                assert_that(result.content[0].text).is_equal_to(
                    "Failed to validate tool parameters: The provided path must exist in order to replace or insert contents into it"
                )
                assert_that(h.messages).is_empty()

        async def it_errors_when_old_str_is_missing(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "str_replace", "path": expected["subject"], "new_str": "replacement"},
                    raise_on_error=False,
                )
                assert_that(result.is_error).is_true()
                assert_that(result.content[0].text).is_equal_to(
                    "Failed to validate tool parameters: str_replace requires old_str"
                )
                assert_that(h.messages).is_empty()
                assert_that(open(expected["subject"]).read()).is_equal_to(expected["value"])

        async def it_deletes_a_line_when_new_str_is_empty(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "str_replace", "path": expected["subject"], "old_str": "charlie\n", "new_str": ""},
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll modify the following file: {expected['subject']} (using tool: write)\n\n"
                    "- 3   : charlie\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                # NOTE: trailing newline consumed as part of old_str — result has no trailing newline
                assert_that(open(expected["subject"]).read()).is_equal_to("alpha\nbravo\nbravo\ndelta")

        async def it_includes_summary_in_elicitation_message(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {
                        "command": "str_replace",
                        "path": expected["subject"],
                        "old_str": "charlie",
                        "new_str": "CHARLIE",
                        "summary": "Uppercase charlie for testing",
                    },
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll modify the following file: {expected['subject']} (using tool: write)\n"
                    "Purpose: Uppercase charlie for testing\n\n"
                    "- 3   : charlie\n"
                    "+    3: CHARLIE\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                assert_that(open(expected["subject"]).read()).is_equal_to("alpha\nbravo\nCHARLIE\nbravo\ndelta\n")

        async def it_replaces_multiline_old_str_with_context_lines(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {
                        "command": "str_replace",
                        "path": expected["subject"],
                        "old_str": "alpha\nbravo\ncharlie",
                        "new_str": "apple\nbravo\ncookie",
                    },
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll modify the following file: {expected['subject']} (using tool: write)\n\n"
                    "- 1   : alpha\n"
                    "+    1: apple\n"
                    "  2, 2: bravo\n"
                    "- 3   : charlie\n"
                    "+    3: cookie\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                assert_that(open(expected["subject"]).read()).is_equal_to("apple\nbravo\ncookie\nbravo\ndelta\n")

    def describe_insert():
        async def it_inserts_after_given_line(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "insert", "path": expected["subject"], "insert_line": 2, "new_str": "inserted"},
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll insert content into file: {expected['subject']} (using tool: write)\n\n"
                    "  1, 1: alpha\n"
                    "  2, 2: bravo\n"
                    "- 3   : charlie\n"
                    "+    3: insertedcharlie\n"
                    "  4, 4: bravo\n"
                    "  5, 5: delta\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                # NOTE: insert does NOT add a newline separator — inserted text is joined directly to adjacent lines
                assert_that(open(expected["subject"]).read()).is_equal_to(
                    "alpha\nbravo\ninsertedcharlie\nbravo\ndelta\n"
                )

        async def it_inserts_at_line_zero(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "insert", "path": expected["subject"], "insert_line": 0, "new_str": "prepended"},
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll insert content into file: {expected['subject']} (using tool: write)\n\n"
                    "- 1   : alpha\n"
                    "+    1: prependedalpha\n"
                    "  2, 2: bravo\n"
                    "  3, 3: charlie\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                # NOTE: same no-newline behaviour at line 0
                assert_that(open(expected["subject"]).read()).is_equal_to(
                    "prependedalpha\nbravo\ncharlie\nbravo\ndelta\n"
                )

        async def it_inserts_at_last_line(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "insert", "path": expected["subject"], "insert_line": 5, "new_str": "at_last_line"},
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll insert content into file: {expected['subject']} (using tool: write)\n\n"
                    "  2, 2: bravo\n"
                    "  3, 3: charlie\n"
                    "  4, 4: bravo\n"
                    "  5, 5: delta\n"
                    "+    6: at_last_line\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                assert_that(open(expected["subject"]).read()).is_equal_to(
                    "alpha\nbravo\ncharlie\nbravo\ndelta\nat_last_line"
                )

        async def it_inserts_beyond_eof(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "insert", "path": expected["subject"], "insert_line": 999, "new_str": "way_beyond"},
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                # NOTE: real tool shows "+    5: way_beyond" (off-by-one display bug — delta is not removed)
                # impl shows "+    6: way_beyond" which is the correct line number
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll insert content into file: {expected['subject']} (using tool: write)\n\n"
                    "  2, 2: bravo\n"
                    "  3, 3: charlie\n"
                    "  4, 4: bravo\n"
                    "  5, 5: delta\n"
                    "+    6: way_beyond\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                assert_that(open(expected["subject"]).read()).is_equal_to(
                    "alpha\nbravo\ncharlie\nbravo\ndelta\nway_beyond"
                )

        async def it_inserts_multiline_new_str(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "insert", "path": expected["subject"], "insert_line": 2, "new_str": "line_a\nline_b"},
                )
                assert_that(result.is_error).is_false()
                assert_that(result.content[0].text).is_equal_to("")
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll insert content into file: {expected['subject']} (using tool: write)\n\n"
                    "  1, 1: alpha\n"
                    "  2, 2: bravo\n"
                    "- 3   : charlie\n"
                    "+    3: line_a\n"
                    "+    4: line_bcharlie\n"
                    "  4, 5: bravo\n"
                    "  5, 6: delta\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
                # NOTE: last line of new_str is jammed into the following line without a newline
                assert_that(open(expected["subject"]).read()).is_equal_to(
                    "alpha\nbravo\nline_a\nline_bcharlie\nbravo\ndelta\n"
                )

        async def it_errors_on_nonexistent_file(mcp, tmp_path):
            path = str(tmp_path / "ghost.txt")
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "insert", "path": path, "insert_line": 1, "new_str": "x"},
                    raise_on_error=False,
                )
                assert_that(result.is_error).is_true()
                assert_that(result.content[0].text).is_equal_to(
                    "Failed to validate tool parameters: The provided path must exist in order to replace or insert contents into it"
                )
                assert_that(h.messages).is_empty()

        async def it_errors_when_new_str_is_missing(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "insert", "path": expected["subject"], "insert_line": 2},
                    raise_on_error=False,
                )
                assert_that(result.is_error).is_true()
                assert_that(result.content[0].text).is_equal_to(
                    "Failed to validate tool parameters: insert requires new_str"
                )
                assert_that(h.messages).is_empty()
                assert_that(open(expected["subject"]).read()).is_equal_to(expected["value"])

    def describe_decline():
        async def it_returns_cancelled_and_does_not_write_when_user_declines(mcp, expected):
            from conftest import make_decline_handler

            h = make_decline_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "create", "path": expected["subject"], "file_text": "should not be written"},
                    raise_on_error=False,
                )
                assert_that(result.is_error).is_true()
                assert_that(result.content[0].text).is_equal_to("Tool use was cancelled by the user")
                assert_that(open(expected["subject"]).read()).is_equal_to(expected["value"])

        async def it_does_not_modify_file_when_user_declines_str_replace(mcp, expected):
            from conftest import make_decline_handler

            h = make_decline_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {"command": "str_replace", "path": expected["subject"], "old_str": "charlie", "new_str": "CHARLIE"},
                    raise_on_error=False,
                )
                assert_that(result.is_error).is_true()
                assert_that(result.content[0].text).is_equal_to("Tool use was cancelled by the user")
                assert_that(open(expected["subject"]).read()).is_equal_to(expected["value"])

    def describe_color():
        async def it_wraps_changed_lines_in_ansi_and_leaves_context_lines_neutral(mcp, expected, monkeypatch):
            monkeypatch.setenv("COLOR", "ascii")
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool(
                    "fs_write",
                    {
                        "command": "str_replace",
                        "path": expected["subject"],
                        "old_str": "alpha\nbravo\ncharlie",
                        "new_str": "apple\nbravo\ncookie",
                    },
                )
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(
                    f"I'll modify the following file: {expected['subject']} (using tool: write)\n\n"
                    "\033[31m- 1   : alpha\033[0m\n"
                    "\033[32m+    1: apple\033[0m\n"
                    "  2, 2: bravo\n"
                    "\033[31m- 3   : charlie\033[0m\n"
                    "\033[32m+    3: cookie\033[0m\n\n\n"
                    "Allow this action? Use 't' to trust (always allow) the 'write' tool for the session. [y/n/t]:"
                )
