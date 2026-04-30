"""Tests for _md_to_storage: markdown → Confluence storage XHTML."""
import pytest
from lxml import etree
from hwiki._md_to_storage import md_to_storage

AC = "http://www.atlassian.com/schema/confluence/4/ac/"
RI = "http://www.atlassian.com/schema/confluence/4/ri/"


def parse(xhtml: str):
    """Wrap output in a root element with ac/ri namespaces and parse."""
    wrapped = (
        f'<root xmlns:ac="{AC}" xmlns:ri="{RI}">'
        f'{xhtml}'
        f'</root>'
    )
    return etree.fromstring(wrapped.encode())


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------

def test_h1():
    root = parse(md_to_storage("# Hello"))
    assert root[0].tag == "h1"
    assert root[0].text == "Hello"


def test_h2():
    root = parse(md_to_storage("## Section"))
    assert root[0].tag == "h2"
    assert root[0].text == "Section"


def test_h3():
    root = parse(md_to_storage("### Sub"))
    assert root[0].tag == "h3"
    assert root[0].text == "Sub"


def test_h4():
    root = parse(md_to_storage("#### Deep"))
    assert root[0].tag == "h4"
    assert root[0].text == "Deep"


# ---------------------------------------------------------------------------
# Paragraph
# ---------------------------------------------------------------------------

def test_paragraph():
    root = parse(md_to_storage("Hello world"))
    assert root[0].tag == "p"
    assert root[0].text == "Hello world"


# ---------------------------------------------------------------------------
# Inline formatting
# ---------------------------------------------------------------------------

def test_bold():
    root = parse(md_to_storage("**bold text**"))
    p = root[0]
    assert p.tag == "p"
    strong = p.find("strong")
    assert strong is not None
    assert strong.text == "bold text"


def test_italic():
    root = parse(md_to_storage("*italic text*"))
    p = root[0]
    em = p.find("em")
    assert em is not None
    assert em.text == "italic text"


def test_inline_code():
    root = parse(md_to_storage("`some_func()`"))
    p = root[0]
    code = p.find("code")
    assert code is not None
    assert code.text == "some_func()"


def test_link():
    root = parse(md_to_storage("[click here](https://example.com)"))
    p = root[0]
    a = p.find("a")
    assert a is not None
    assert a.get("href") == "https://example.com"
    assert a.text == "click here"


def test_image():
    root = parse(md_to_storage("![alt text](https://img.example.com/pic.png)"))
    p = root[0]
    img = p.find(f"{{{AC}}}image")
    assert img is not None
    url_el = img.find(f"{{{RI}}}url")
    assert url_el is not None
    assert url_el.get(f"{{{RI}}}value") == "https://img.example.com/pic.png"


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

def test_unordered_list():
    root = parse(md_to_storage("- Alpha\n- Beta\n- Gamma"))
    ul = root[0]
    assert ul.tag == "ul"
    items = ul.findall("li")
    assert len(items) == 3
    assert items[0].text == "Alpha"
    assert items[1].text == "Beta"


def test_ordered_list():
    root = parse(md_to_storage("1. First\n2. Second\n3. Third"))
    ol = root[0]
    assert ol.tag == "ol"
    items = ol.findall("li")
    assert len(items) == 3
    assert items[0].text == "First"


def test_nested_list():
    md = "- Item 1\n  - Nested A\n  - Nested B\n- Item 2"
    root = parse(md_to_storage(md))
    ul = root[0]
    assert ul.tag == "ul"
    # First li should contain a nested ul
    first_li = ul[0]
    nested_ul = first_li.find("ul")
    assert nested_ul is not None
    nested_items = nested_ul.findall("li")
    assert len(nested_items) == 2


# ---------------------------------------------------------------------------
# Code block
# ---------------------------------------------------------------------------

def test_code_block_with_language():
    md = "```python\nprint('hello')\n```"
    root = parse(md_to_storage(md))
    macro = root[0]
    assert macro.tag == f"{{{AC}}}structured-macro"
    assert macro.get(f"{{{AC}}}name") == "code"

    lang_param = None
    for child in macro:
        if child.tag == f"{{{AC}}}parameter" and child.get(f"{{{AC}}}name") == "language":
            lang_param = child
            break
    assert lang_param is not None
    assert lang_param.text == "python"

    body = macro.find(f"{{{AC}}}plain-text-body")
    assert body is not None
    assert "print('hello')" in (body.text or "")


def test_code_block_no_language():
    md = "```\nx = 1\n```"
    root = parse(md_to_storage(md))
    macro = root[0]
    assert macro.tag == f"{{{AC}}}structured-macro"
    assert macro.get(f"{{{AC}}}name") == "code"


# ---------------------------------------------------------------------------
# Blockquote
# ---------------------------------------------------------------------------

def test_blockquote():
    root = parse(md_to_storage("> This is a quote"))
    bq = root[0]
    assert bq.tag == "blockquote"
    p = bq.find("p")
    assert p is not None
    assert "This is a quote" in (p.text or "")


# ---------------------------------------------------------------------------
# Callout macros
# ---------------------------------------------------------------------------

def test_info_callout():
    md = "> [!INFO]\n> Important information"
    root = parse(md_to_storage(md))
    macro = root[0]
    assert macro.tag == f"{{{AC}}}structured-macro"
    assert macro.get(f"{{{AC}}}name") == "info"
    body = macro.find(f"{{{AC}}}rich-text-body")
    assert body is not None


def test_warning_callout():
    md = "> [!WARNING]\n> Watch out!"
    root = parse(md_to_storage(md))
    macro = root[0]
    assert macro.get(f"{{{AC}}}name") == "warning"


def test_note_callout():
    md = "> [!NOTE]\n> Take note of this"
    root = parse(md_to_storage(md))
    macro = root[0]
    assert macro.get(f"{{{AC}}}name") == "note"


def test_tip_callout():
    md = "> [!TIP]\n> Here is a tip"
    root = parse(md_to_storage(md))
    macro = root[0]
    assert macro.get(f"{{{AC}}}name") == "tip"


# ---------------------------------------------------------------------------
# Horizontal rule
# ---------------------------------------------------------------------------

def test_hr():
    root = parse(md_to_storage("---"))
    assert root[0].tag == "hr"


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------

def test_simple_table():
    md = "| Name | Age |\n|------|-----|\n| Alice | 30 |\n| Bob | 25 |"
    root = parse(md_to_storage(md))
    table = root[0]
    assert table.tag == "table"
    tbody = table.find("tbody")
    assert tbody is not None
    rows = tbody.findall("tr")
    assert len(rows) == 3  # header + 2 data rows

    # Header row should have th elements
    header_cells = rows[0].findall("th")
    assert len(header_cells) == 2
    assert header_cells[0].text == "Name"
    assert header_cells[1].text == "Age"

    # Data rows should have td elements
    data_cells = rows[1].findall("td")
    assert len(data_cells) == 2
    assert data_cells[0].text == "Alice"
