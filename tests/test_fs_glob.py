import json

import pytest
from assertpy import assert_that
from conftest import make_capture_handler, make_decline_handler
from fastmcp.client import Client


@pytest.fixture(autouse=True)
def expected(sandbox):
    root = sandbox / "glob_test"
    (root / "sub" / "deep").mkdir(parents=True)
    for p in ["a.txt", "b.txt", "c.py", "sub/d.txt", "sub/e.py", "sub/deep/f.txt"]:
        (root / p).touch()
    return {"root": str(root)}


def result_data(result):
    return json.loads(result.content[0].text)


def assert_glob_result(result, expected):
    """Assert glob JSON result, comparing filePaths as a set (order-independent)."""
    data = result_data(result)
    expected_paths = set(expected.pop("filePaths", []))
    actual_paths = set(data.pop("filePaths", []))
    assert_that(data).is_equal_to(expected)
    assert_that(actual_paths).is_equal_to(expected_paths)


def describe_glob():

    def describe_basic_pattern():
        async def it_finds_matching_files(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.txt", "path": expected["root"]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.txt in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {
                    "filePaths": [f"{expected["root"]}/a.txt", f"{expected["root"]}/b.txt", f"{expected["root"]}/sub/d.txt", f"{expected["root"]}/sub/deep/f.txt"],
                    "totalFiles": 4,
                    "truncated": False,
                })

        async def it_returns_empty_when_no_matches(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.rb", "path": expected["root"]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.rb in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {
                    "filePaths": [],
                    "message": "No files found matching pattern: **/*.rb",
                    "totalFiles": 0,
                    "truncated": False,
                })

    def describe_limit():
        async def it_truncates_results_when_limit_exceeded(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.txt", "path": expected["root"], "limit": 2})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.txt in {expected["root"]} (using tool: glob)")
                data = result_data(result)
                assert_that(data["totalFiles"]).is_equal_to(4)
                assert_that(data["truncated"]).is_true()
                assert_that(data["filePaths"]).is_length(2)

        async def it_does_not_truncate_when_under_limit(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.txt", "path": expected["root"], "limit": 100})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.txt in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {
                    "filePaths": [f"{expected["root"]}/a.txt", f"{expected["root"]}/b.txt", f"{expected["root"]}/sub/d.txt", f"{expected["root"]}/sub/deep/f.txt"],
                    "totalFiles": 4,
                    "truncated": False,
                })

        async def it_does_not_truncate_when_limit_equals_total(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.txt", "path": expected["root"], "limit": 4})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.txt in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {
                    "filePaths": [f"{expected["root"]}/a.txt", f"{expected["root"]}/b.txt", f"{expected["root"]}/sub/d.txt", f"{expected["root"]}/sub/deep/f.txt"],
                    "totalFiles": 4,
                    "truncated": False,
                })

        async def it_returns_empty_with_truncated_true_when_limit_is_zero(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.txt", "path": expected["root"], "limit": 0})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.txt in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {"filePaths": [], "totalFiles": 4, "truncated": True})

    def describe_max_depth():
        async def it_excludes_files_beyond_max_depth(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.txt", "path": expected["root"], "max_depth": 1})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.txt in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {
                    "filePaths": [f"{expected["root"]}/a.txt", f"{expected["root"]}/b.txt"],
                    "totalFiles": 2,
                    "truncated": False,
                })

        async def it_returns_nothing_when_max_depth_is_zero(mcp, expected):
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.txt", "path": expected["root"], "max_depth": 0})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.txt in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {
                    "filePaths": [],
                    "message": "No files found matching pattern: **/*.txt",
                    "totalFiles": 0,
                    "truncated": False,
                })

        async def it_totalfiles_reflects_depth_constrained_count_not_global(mcp, expected):
            # totalFiles=2 (depth-constrained), not 4 (all files) — max_depth constrains the walk itself
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.txt", "path": expected["root"], "max_depth": 1, "limit": 999})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.txt in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {
                    "filePaths": [f"{expected["root"]}/a.txt", f"{expected["root"]}/b.txt"],
                    "totalFiles": 2,
                    "truncated": False,
                })

    def describe_pattern_syntax():
        async def it_treats_single_star_same_as_double_star(mcp, expected):
            # *.txt with no max_depth recurses all depths — identical to **/*.txt
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "*.txt", "path": expected["root"]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: *.txt in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {
                    "filePaths": [f"{expected["root"]}/a.txt", f"{expected["root"]}/b.txt", f"{expected["root"]}/sub/d.txt", f"{expected["root"]}/sub/deep/f.txt"],
                    "totalFiles": 4,
                    "truncated": False,
                })

        async def it_single_star_respects_max_depth(mcp, expected):
            # *.txt with max_depth=1 only returns root-level files
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "*.txt", "path": expected["root"], "max_depth": 1})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: *.txt in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {
                    "filePaths": [f"{expected["root"]}/a.txt", f"{expected["root"]}/b.txt"],
                    "totalFiles": 2,
                    "truncated": False,
                })

        async def it_supports_single_char_wildcard(mcp, expected):
            # ? matches any single character
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.tx?", "path": expected["root"]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.tx? in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {
                    "filePaths": [f"{expected["root"]}/a.txt", f"{expected["root"]}/b.txt", f"{expected["root"]}/sub/d.txt", f"{expected["root"]}/sub/deep/f.txt"],
                    "totalFiles": 4,
                    "truncated": False,
                })

        async def it_does_not_support_regex_quantifiers(mcp, expected):
            # + is not a valid glob quantifier — no matches
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.tx+", "path": expected["root"]})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.tx+ in {expected["root"]} (using tool: glob)")
                assert_glob_result(result, {
                    "filePaths": [],
                    "message": "No files found matching pattern: **/*.tx+",
                    "totalFiles": 0,
                    "truncated": False,
                })

    def describe_error_cases():
        async def it_returns_error_json_on_nonexistent_path(mcp, expected):
            # NOTE: elicitation DOES fire — error is returned as JSON after acceptance
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.txt", "path": f"{expected["root"]}/no_such_dir"})
                assert_that(result.is_error).is_false()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.txt in {expected["root"]}/no_such_dir (using tool: glob)")
                assert_glob_result(result, {"filePaths": [], "error": f"Path does not exist: {expected["root"]}/no_such_dir"})

        async def it_errors_on_empty_pattern(mcp, expected):
            # empty pattern fails validation — no elicitation fires
            h = make_capture_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "", "path": expected["root"]}, raise_on_error=False)
                assert_that(result.is_error).is_true()
                assert_that(h.messages).is_empty()
                assert_that(result.content[0].text).is_equal_to("Failed to validate tool parameters: Glob pattern cannot be empty")

    def describe_decline():
        async def it_returns_cancelled_when_user_declines(mcp, expected):
            h = make_decline_handler()
            async with Client(transport=mcp, elicitation_handler=h) as client:
                result = await client.call_tool("fs_glob", {"pattern": "**/*.txt", "path": expected["root"]}, raise_on_error=False)
                assert_that(result.is_error).is_true()
                assert_that(h.messages[0]).is_equal_to(f"Searching for files: **/*.txt in {expected["root"]} (using tool: glob)")
                assert_that(result.content[0].text).is_equal_to("Tool use was cancelled by the user")
