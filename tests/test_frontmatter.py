import pytest
from pathlib import Path
from hwiki._frontmatter import read_frontmatter, write_frontmatter


def test_round_trip_basic(tmp_path):
    p = tmp_path / "page.md"
    meta = {"id": "123", "title": "My Page", "version": 5, "space": "ENG", "parent_id": None}
    body = "# Hello\n\nContent.\n"
    write_frontmatter(p, meta, body)
    meta2, body2 = read_frontmatter(p)
    assert meta2["id"] == "123"
    assert meta2["title"] == "My Page"
    assert meta2["version"] == 5
    assert meta2["parent_id"] is None
    assert body2 == body


def test_no_frontmatter(tmp_path):
    p = tmp_path / "plain.md"
    p.write_text("# No front-matter\n\nJust text.\n")
    meta, body = read_frontmatter(p)
    assert meta == {}
    assert "No front-matter" in body


def test_russian_title(tmp_path):
    p = tmp_path / "page.md"
    meta = {"id": "477874699", "title": "Карточка проекта: тест", "version": 42, "space": "WBS", "parent_id": None}
    write_frontmatter(p, meta, "# Тест\n")
    meta2, _ = read_frontmatter(p)
    assert meta2["title"] == "Карточка проекта: тест"
    assert meta2["version"] == 42


def test_special_chars_in_title(tmp_path):
    p = tmp_path / "page.md"
    meta = {"title": 'He said "hello"', "version": 1}
    write_frontmatter(p, meta, "body\n")
    meta2, _ = read_frontmatter(p)
    assert meta2["title"] == 'He said "hello"'


def test_body_preserved(tmp_path):
    p = tmp_path / "page.md"
    body = "# Heading\n\n- item 1\n- item 2\n\n```python\nprint('hi')\n```\n"
    write_frontmatter(p, {"id": "1", "version": 1}, body)
    _, body2 = read_frontmatter(p)
    assert body2 == body
