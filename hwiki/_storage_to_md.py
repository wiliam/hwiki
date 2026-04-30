from __future__ import annotations

from lxml import etree

AC = "http://www.atlassian.com/schema/confluence/4/ac/"
RI = "http://www.atlassian.com/schema/confluence/4/ri/"

WRAPPER = (
    '<root xmlns:ac="http://www.atlassian.com/schema/confluence/4/ac/"'
    ' xmlns:ri="http://www.atlassian.com/schema/confluence/4/ri/">'
    '{}'
    '</root>'
)

_CALLOUT_MAP = {
    "info": "INFO",
    "warning": "WARNING",
    "note": "NOTE",
    "tip": "TIP",
}


def storage_to_md(xhtml: str) -> str:
    """Convert Confluence storage XHTML to markdown."""
    root = etree.fromstring(WRAPPER.format(xhtml).encode())
    lines = []
    for child in root:
        result = _node_to_md(child)
        if result is not None:
            lines.append(result)
    return "\n\n".join(filter(None, lines)).strip()


def _inline(elem) -> str:
    """Render mixed text + child elements as inline markdown."""
    parts = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        parts.append(_inline_node(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _inline_node(elem) -> str:
    """Render a single inline element as markdown."""
    tag = elem.tag
    if tag == "strong":
        return f"**{_inline(elem)}**"
    if tag == "em":
        return f"*{_inline(elem)}*"
    if tag == "code":
        return f"`{_inline(elem)}`"
    if tag == "a":
        href = elem.get("href", "")
        return f"[{_inline(elem)}]({href})"
    if tag == f"{{{AC}}}image":
        url_el = elem.find(f"{{{RI}}}url")
        url = url_el.get(f"{{{RI}}}value", "") if url_el is not None else ""
        alt = elem.get("alt", "")
        return f"![{alt}]({url})"
    if tag == "br":
        return "\n"
    # Fallback: just return text content
    return _inline(elem)


def _node_to_md(elem) -> str | None:
    """Convert a block-level element to markdown string."""
    tag = elem.tag

    # Headings
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(tag[1])
        return "#" * level + " " + _inline(elem)

    # Paragraph
    if tag == "p":
        return _inline(elem)

    # Horizontal rule
    if tag == "hr":
        return "---"

    # Unordered list
    if tag == "ul":
        return _list_to_md(elem, ordered=False, depth=0)

    # Ordered list
    if tag == "ol":
        return _list_to_md(elem, ordered=True, depth=0)

    # Blockquote
    if tag == "blockquote":
        lines = []
        for child in elem:
            text = _node_to_md(child)
            if text:
                for line in text.splitlines():
                    lines.append(f"> {line}")
        return "\n".join(lines)

    # Table
    if tag == "table":
        return _table_to_md(elem)

    # Confluence structured macro
    if tag == f"{{{AC}}}structured-macro":
        return _macro_to_md(elem)

    # Confluence image
    if tag == f"{{{AC}}}image":
        return _inline_node(elem)

    # Handle inline elements used at block level
    if tag in ("strong", "em", "code", "a"):
        return _inline_node(elem)

    # Unknown / unsupported
    return None


def _list_to_md(elem, ordered: bool, depth: int) -> str:
    prefix = "  " * depth
    lines = []
    for i, li in enumerate(elem, start=1):
        if li.tag != "li":
            continue
        # Collect inline text and nested lists separately
        inline_parts = []
        nested = []
        if li.text:
            inline_parts.append(li.text)
        for child in li:
            if child.tag in ("ul", "ol"):
                nested.append(child)
            else:
                inline_parts.append(_inline_node(child))
            if child.tail:
                inline_parts.append(child.tail)
        item_text = "".join(inline_parts).strip()
        bullet = f"{i}." if ordered else "-"
        lines.append(f"{prefix}{bullet} {item_text}")
        for nested_list in nested:
            nested_ordered = nested_list.tag == "ol"
            nested_md = _list_to_md(nested_list, ordered=nested_ordered, depth=depth + 1)
            lines.append(nested_md)
    return "\n".join(lines)


def _table_to_md(elem) -> str:
    rows = []
    # Find all tr elements (may be in tbody)
    for tr in elem.iter("tr"):
        cells = []
        is_header_row = False
        for cell in tr:
            if cell.tag == "th":
                is_header_row = True
                cells.append(_inline(cell).strip())
            elif cell.tag == "td":
                cells.append(_inline(cell).strip())
        if cells:
            rows.append((cells, is_header_row))

    if not rows:
        return ""

    lines = []
    header_written = False
    for cells, is_header in rows:
        row_str = "| " + " | ".join(cells) + " |"
        lines.append(row_str)
        if is_header and not header_written:
            sep = "| " + " | ".join("---" for _ in cells) + " |"
            lines.append(sep)
            header_written = True

    return "\n".join(lines)


def _macro_to_md(elem) -> str:
    name = elem.get(f"{{{AC}}}name", "")

    # Code block macro
    if name == "code":
        lang = ""
        content = ""
        for child in elem:
            if child.tag == f"{{{AC}}}parameter" and child.get(f"{{{AC}}}name") == "language":
                lang = (child.text or "").strip()
            if child.tag == f"{{{AC}}}plain-text-body":
                content = child.text or ""
        return f"```{lang}\n{content}\n```"

    # Callout macros
    if name in _CALLOUT_MAP:
        keyword = _CALLOUT_MAP[name]
        body_elem = elem.find(f"{{{AC}}}rich-text-body")
        if body_elem is None:
            return f"> [!{keyword}]"
        # Collect all block children of rich-text-body
        parts = []
        for child in body_elem:
            text = _node_to_md(child)
            if text:
                parts.append(text)
        if not parts:
            # Try inline text
            text = _inline(body_elem).strip()
            if text:
                parts.append(text)
        lines = [f"> [!{keyword}]"]
        for part in parts:
            for line in part.splitlines():
                lines.append(f"> {line}")
        return "\n".join(lines)

    # Unsupported macro
    return f"<!-- hwiki: unsupported {name} -->"
