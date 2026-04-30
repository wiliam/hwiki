import json
import pytest
from pathlib import Path
from hwiki._manifest import (
    make_slug, page_filename, content_hash, load_manifest, save_manifest,
    find_manifest_dir, MANIFEST_FILE
)


def test_make_slug_english():
    assert make_slug("Hello World") == "hello-world"


def test_make_slug_russian():
    slug = make_slug("Карточка проекта Результативность")
    assert slug  # not empty
    assert all(c.isalnum() or c == '-' for c in slug)
    assert slug == slug.lower()


def test_make_slug_truncation():
    long_title = "A" * 100
    assert len(make_slug(long_title)) <= 60


def test_page_filename_basic():
    fn = page_filename("123", "My Page")
    assert fn.startswith("123-")
    assert fn.endswith(".md")


def test_page_filename_russian():
    fn = page_filename("477874699", "Карточка проекта")
    assert fn.startswith("477874699-")
    assert fn.endswith(".md")


def test_page_filename_empty_slug():
    fn = page_filename("123", "!!!")  # all special chars — slug might be empty
    assert fn == "123.md" or fn.startswith("123-")


def test_content_hash():
    h = content_hash("hello")
    assert h.startswith("sha256:")
    assert h == content_hash("hello")
    assert h != content_hash("world")


def test_save_load_manifest(tmp_path):
    m = {
        "host": "https://wiki.example.com",
        "space": "ENG",
        "root_id": "123",
        "pulled_at": "2026-01-01T00:00:00+00:00",
        "pages": {
            "123": {
                "title": "Root",
                "space": "ENG",
                "version": 1,
                "parent_id": None,
                "path": "123-root.md",
                "content_hash": "sha256:abc",
            }
        }
    }
    save_manifest(tmp_path, m)
    loaded = load_manifest(tmp_path)
    assert loaded["root_id"] == "123"
    assert loaded["pages"]["123"]["title"] == "Root"


def test_find_manifest_dir(tmp_path):
    (tmp_path / MANIFEST_FILE).write_text("{}")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    found = find_manifest_dir(sub)
    assert found == tmp_path


def test_find_manifest_dir_not_found(tmp_path):
    result = find_manifest_dir(tmp_path)
    assert result is None
