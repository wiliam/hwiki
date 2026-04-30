"""Tests for _storage_to_md: Confluence storage XHTML → markdown."""
import pytest
from hwiki._storage_to_md import storage_to_md

AC = 'xmlns:ac="http://www.atlassian.com/schema/confluence/4/ac/"'
RI = 'xmlns:ri="http://www.atlassian.com/schema/confluence/4/ri/"'
NS = f'{AC} {RI}'


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------

def test_h1():
    assert storage_to_md("<h1>Hello</h1>").strip() == "# Hello"


def test_h2():
    assert storage_to_md("<h2>Section</h2>").strip() == "## Section"


def test_h3():
    assert storage_to_md("<h3>Sub</h3>").strip() == "### Sub"


def test_h4():
    assert storage_to_md("<h4>Deep</h4>").strip() == "#### Deep"


# ---------------------------------------------------------------------------
# Paragraph
# ---------------------------------------------------------------------------

def test_paragraph():
    assert storage_to_md("<p>Hello world</p>").strip() == "Hello world"


# ---------------------------------------------------------------------------
# Inline formatting
# ---------------------------------------------------------------------------

def test_bold():
    assert storage_to_md("<p><strong>Bold</strong></p>").strip() == "**Bold**"


def test_italic():
    assert storage_to_md("<p><em>Italic</em></p>").strip() == "*Italic*"


def test_inline_code():
    assert storage_to_md("<p><code>some_code()</code></p>").strip() == "`some_code()`"


def test_link():
    result = storage_to_md('<p><a href="https://example.com">click</a></p>').strip()
    assert result == "[click](https://example.com)"


# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------

def test_image():
    xhtml = f'<ac:image {NS}><ri:url ri:value="https://img.example.com/x.png"/></ac:image>'
    result = storage_to_md(xhtml).strip()
    assert "https://img.example.com/x.png" in result
    assert result.startswith("![")


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

def test_unordered_list():
    xhtml = "<ul><li>Alpha</li><li>Beta</li></ul>"
    result = storage_to_md(xhtml).strip()
    assert "- Alpha" in result
    assert "- Beta" in result


def test_ordered_list():
    xhtml = "<ol><li>First</li><li>Second</li></ol>"
    result = storage_to_md(xhtml).strip()
    assert "1. First" in result
    assert "2. Second" in result


# ---------------------------------------------------------------------------
# Horizontal rule
# ---------------------------------------------------------------------------

def test_hr():
    assert storage_to_md("<hr/>").strip() == "---"


# ---------------------------------------------------------------------------
# Code block macro
# ---------------------------------------------------------------------------

def test_code_block_with_language():
    xhtml = (
        f'<ac:structured-macro {NS} ac:name="code">'
        f'<ac:parameter ac:name="language">python</ac:parameter>'
        f'<ac:plain-text-body><![CDATA[print("hi")]]></ac:plain-text-body>'
        f'</ac:structured-macro>'
    )
    result = storage_to_md(xhtml)
    assert "```python" in result
    assert 'print("hi")' in result
    assert "```" in result


def test_code_block_no_language():
    xhtml = (
        f'<ac:structured-macro {NS} ac:name="code">'
        f'<ac:parameter ac:name="language"></ac:parameter>'
        f'<ac:plain-text-body><![CDATA[x = 1]]></ac:plain-text-body>'
        f'</ac:structured-macro>'
    )
    result = storage_to_md(xhtml)
    assert "```" in result
    assert "x = 1" in result


# ---------------------------------------------------------------------------
# Blockquote
# ---------------------------------------------------------------------------

def test_blockquote():
    xhtml = "<blockquote><p>quoted text</p></blockquote>"
    result = storage_to_md(xhtml).strip()
    assert result.startswith(">")
    assert "quoted text" in result


# ---------------------------------------------------------------------------
# Callout macros
# ---------------------------------------------------------------------------

def test_callout_info():
    xhtml = (
        f'<ac:structured-macro {NS} ac:name="info">'
        f'<ac:rich-text-body><p>Info message</p></ac:rich-text-body>'
        f'</ac:structured-macro>'
    )
    result = storage_to_md(xhtml)
    assert "> [!INFO]" in result
    assert "Info message" in result


def test_callout_warning():
    xhtml = (
        f'<ac:structured-macro {NS} ac:name="warning">'
        f'<ac:rich-text-body><p>Watch out</p></ac:rich-text-body>'
        f'</ac:structured-macro>'
    )
    result = storage_to_md(xhtml)
    assert "> [!WARNING]" in result
    assert "Watch out" in result


def test_callout_note():
    xhtml = (
        f'<ac:structured-macro {NS} ac:name="note">'
        f'<ac:rich-text-body><p>Take note</p></ac:rich-text-body>'
        f'</ac:structured-macro>'
    )
    result = storage_to_md(xhtml)
    assert "> [!NOTE]" in result


def test_callout_tip():
    xhtml = (
        f'<ac:structured-macro {NS} ac:name="tip">'
        f'<ac:rich-text-body><p>Pro tip</p></ac:rich-text-body>'
        f'</ac:structured-macro>'
    )
    result = storage_to_md(xhtml)
    assert "> [!TIP]" in result


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------

def test_table():
    xhtml = (
        "<table><tbody>"
        "<tr><th>Name</th><th>Age</th></tr>"
        "<tr><td>Alice</td><td>30</td></tr>"
        "</tbody></table>"
    )
    result = storage_to_md(xhtml)
    assert "Name" in result
    assert "Age" in result
    assert "Alice" in result
    assert "30" in result
    assert "|" in result
    assert "---" in result


# ---------------------------------------------------------------------------
# Unsupported macro → placeholder comment
# ---------------------------------------------------------------------------

def test_unsupported_macro():
    xhtml = (
        f'<ac:structured-macro {NS} ac:name="jira">'
        f'<ac:parameter ac:name="key">PROJ-123</ac:parameter>'
        f'</ac:structured-macro>'
    )
    result = storage_to_md(xhtml)
    assert "<!-- hwiki: unsupported jira -->" in result


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------

def test_roundtrip_heading_paragraph():
    from hwiki._md_to_storage import md_to_storage

    md_input = "# Title\n\nSome paragraph text."
    xhtml = md_to_storage(md_input)
    result = storage_to_md(xhtml).strip()
    assert "# Title" in result
    assert "Some paragraph text." in result


def test_roundtrip_code_block():
    from hwiki._md_to_storage import md_to_storage

    md_input = "```python\nprint('hello')\n```"
    xhtml = md_to_storage(md_input)
    result = storage_to_md(xhtml)
    assert "```python" in result
    assert "print('hello')" in result
