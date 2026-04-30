#!/usr/bin/env python3
"""
Live smoke test against a real Confluence instance.
Run manually: python tests/smoke.py

Requires ~/.hwiki_config and a logged-in session (hwiki login).
Creates a page in the space from HWIKI_TEST_SPACE env var (default: SANDBOX),
reads it back, updates it, searches for it. Prints PASS/FAIL per step.

The created page is NOT automatically deleted (hwiki has no delete command).
"""
import json
import os
import subprocess
import sys

SPACE = os.environ.get("HWIKI_TEST_SPACE", "SANDBOX")


def run(args, input=None):
    """Run hwiki CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["hwiki"] + args,
        capture_output=True,
        text=True,
        input=input,
    )
    return result.returncode, result.stdout, result.stderr


def check(label, ok, detail=""):
    if ok:
        print(f"PASS  {label}")
    else:
        print(f"FAIL  {label}: {detail}")
        sys.exit(1)


def main():
    title = "hwiki-smoke-test"

    # create
    rc, out, err = run(
        ["create", "--space", SPACE, "--title", title, "--stdin"],
        input="# Smoke Test\n\nThis is a test page.\n",
    )
    check("create page", rc == 0, err)

    # extract page id from "created page id=... title=..."
    page_id = None
    for part in out.split():
        if part.startswith("id="):
            page_id = part[3:]
    check("create returned id", page_id is not None, out)

    # get raw
    rc, out, err = run(["get", page_id, "--raw"])
    check("get page raw", rc == 0, err)

    # get json
    rc, out, err = run(["get", page_id, "--json"])
    check("get page json", rc == 0, err)
    page = json.loads(out)
    check("json has id", page["id"] == page_id)

    # update
    rc, out, err = run(
        ["update", page_id, "--title", title, "--version", "auto", "--stdin"],
        input="# Updated\n\nUpdated content.\n",
    )
    check("update page", rc == 0, err)

    # search
    rc, out, err = run(["search", f'space = {SPACE} AND title = "{title}"', "-n", "5"])
    check("search finds page", rc == 0 and page_id in out, err + out)

    # search --json
    rc, out, err = run(["search", f'space = {SPACE} AND title = "{title}"', "--json"])
    check("search --json", rc == 0, err)
    hits = json.loads(out)
    check("search --json returns list", isinstance(hits, list), out)

    print(f"NOTE  page {page_id} left in {SPACE} — delete manually")
    print("DONE")


if __name__ == "__main__":
    main()
