from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import quote
from lxml import etree

AC = "http://www.atlassian.com/schema/confluence/4/ac/"
RI = "http://www.atlassian.com/schema/confluence/4/ri/"

WRAPPER = (
    '<root xmlns:ac="http://www.atlassian.com/schema/confluence/4/ac/"'
    ' xmlns:ri="http://www.atlassian.com/schema/confluence/4/ri/">'
    '{}'
    '</root>'
)

def _table_to_html(elem, ctx: _Ctx) -> str:
    """Render spanning table as HTML with converted cell content."""
    lines = ["<table>"]
    tbody = elem.find("tbody")
    rows_container = tbody if tbody is not None else elem
    for tr in rows_container:
        if tr.tag != "tr":
            continue
        lines.append("<tr>")
        for cell in tr:
            if cell.tag not in ("th", "td"):
                continue
            rs = cell.get("rowspan", "1")
            cs = cell.get("colspan", "1")
            attrs = ""
            if rs != "1":
                attrs += f' rowspan="{rs}"'
            if cs != "1":
                attrs += f' colspan="{cs}"'
            blocks = [r for child in cell if (r := _node_to_md(child, ctx))]
            content = "<br/>".join(b.strip() for b in blocks if b.strip()) if blocks else _inline(cell, ctx).strip()
            lines.append(f"<{cell.tag}{attrs}>{content}</{cell.tag}>")
        lines.append("</tr>")
    lines.append("</table>")
    return "\n".join(lines)


def _raw_xml(elem) -> str:
    xml = etree.tostring(elem, encoding="unicode")
    return f"```xml\n{xml}\n```"


_CALLOUT_MAP = {
    "info": "INFO",
    "warning": "WARNING",
    "note": "NOTE",
    "tip": "TIP",
}


@dataclass
class _Ctx:
    host: str = ""
    space_key: str = ""
    page_id: str = ""
    link_map: dict = field(default_factory=dict)       # {page_id → filename e.g. "123-slug.md"}
    title_index: dict = field(default_factory=dict)    # {(space, title) → page_id}
    attachment_dir_rel: str = ""                       # when set, use local paths for ri:attachment


def storage_to_md(
    xhtml: str,
    host: str = "",
    space_key: str = "",
    page_id: str = "",
    link_map: dict[str, str] | None = None,
    title_index: dict[tuple[str, str], str] | None = None,
    attachment_dir_rel: str = "",
) -> str:
    """Convert Confluence storage XHTML to markdown."""
    ctx = _Ctx(
        host=host.rstrip("/"),
        space_key=space_key,
        page_id=page_id,
        link_map=link_map or {},
        title_index=title_index or {},
        attachment_dir_rel=attachment_dir_rel,
    )
    root = etree.fromstring(WRAPPER.format(xhtml).encode())
    lines = [r for child in root if (r := _node_to_md(child, ctx)) is not None]
    return "\n\n".join(filter(None, lines)).strip()


def _inline(elem, ctx: _Ctx) -> str:
    """Render mixed text + child elements as inline markdown."""
    parts = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        parts.append(_inline_node(child, ctx))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _inline_node(elem, ctx: _Ctx) -> str:
    """Render a single inline element as markdown."""
    tag = elem.tag
    if tag == "strong":
        return f"**{_inline(elem, ctx)}**"
    if tag == "em":
        return f"*{_inline(elem, ctx)}*"
    if tag == "code":
        return f"`{_inline(elem, ctx)}`"
    if tag == "a":
        href = elem.get("href", "")
        return f"[{_inline(elem, ctx)}]({href})"
    if tag == f"{{{AC}}}image":
        url_el = elem.find(f"{{{RI}}}url")
        if url_el is not None:
            url = url_el.get(f"{{{RI}}}value", "")
        else:
            att_el = elem.find(f"{{{RI}}}attachment")
            if att_el is not None:
                filename = att_el.get(f"{{{RI}}}filename", "")
                if ctx.attachment_dir_rel and ctx.page_id and filename:
                    url = f"{ctx.attachment_dir_rel.rstrip('/')}/{ctx.page_id}_{filename}"
                elif ctx.host and ctx.page_id and filename:
                    url = f"{ctx.host}/download/attachments/{ctx.page_id}/{quote(filename, safe='')}"
                else:
                    url = ""
            else:
                url = ""
        alt = elem.get("alt", "")
        return f"![{alt}]({url})"
    if tag == f"{{{AC}}}link":
        return _ac_link_to_md(elem, ctx)
    if tag == "br":
        return "\n"
    if tag == "span":
        return _inline(elem, ctx)
    if tag == f"{{{AC}}}inline-comment-marker":
        return _inline(elem, ctx)
    # Fallback: just return text content
    return _inline(elem, ctx)


def _ac_link_to_md(elem, ctx: _Ctx) -> str:
    """Render ac:link (internal page/attachment link) as markdown."""
    # Extract link text
    text = ""
    plain_body = elem.find(f"{{{AC}}}plain-text-link-body")
    if plain_body is not None:
        text = (plain_body.text or "").strip()
    if not text:
        rich_body = elem.find(f"{{{AC}}}link-body")
        if rich_body is not None:
            text = _inline(rich_body, ctx).strip()

    # User mention — no display name in storage format, preserve userkey for later resolution
    user_el = elem.find(f"{{{RI}}}user")
    if user_el is not None:
        userkey = user_el.get(f"{{{RI}}}userkey", "")
        if text:
            return f"@{text}"
        return f"@mention_unresolved:{userkey}" if userkey else "@mention"

    url = ""
    page_el = elem.find(f"{{{RI}}}page")
    if page_el is not None:
        title = page_el.get(f"{{{RI}}}content-title", "")
        space = page_el.get(f"{{{RI}}}space-key", "") or ctx.space_key
        if not text:
            text = title

        # Check title_index first (sync: link to a pulled page → local file)
        target_id = ctx.title_index.get((space, title)) or ctx.title_index.get(("", title))
        if target_id and target_id in ctx.link_map:
            url = f"./{ctx.link_map[target_id]}"
        elif ctx.host and space and title:
            url = f"{ctx.host}/display/{space}/{quote(title, safe='')}"

    if not text:
        text = "[link]"
    return f"[{text}]({url})" if url else text


def _node_to_md(elem, ctx: _Ctx) -> str | None:
    """Convert a block-level element to markdown string."""
    tag = elem.tag

    # Headings
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(tag[1])
        return "#" * level + " " + _inline(elem, ctx)

    # Paragraph
    if tag == "p":
        return _inline(elem, ctx)

    # Horizontal rule
    if tag == "hr":
        return "---"

    # Unordered list
    if tag == "ul":
        return _list_to_md(elem, ordered=False, depth=0, ctx=ctx)

    # Ordered list
    if tag == "ol":
        return _list_to_md(elem, ordered=True, depth=0, ctx=ctx)

    # Blockquote
    if tag == "blockquote":
        lines = []
        for child in elem:
            text = _node_to_md(child, ctx)
            if text:
                for line in text.splitlines():
                    lines.append(f"> {line}")
        return "\n".join(lines)

    # Table
    if tag == "table":
        return _table_to_md(elem, ctx)

    # Confluence structured macro
    if tag == f"{{{AC}}}structured-macro":
        return _macro_to_md(elem, ctx)

    # Confluence image
    if tag == f"{{{AC}}}image":
        return _inline_node(elem, ctx)

    # br at block level — skip
    if tag == "br":
        return None

    # div — HTML container, flatten content
    if tag == "div":
        parts = [r for child in elem if (r := _node_to_md(child, ctx))]
        return "\n\n".join(filter(None, parts)) or _inline(elem, ctx) or None

    # ac:layout / ac:layout-section / ac:layout-cell — flatten content
    if tag in (f"{{{AC}}}layout", f"{{{AC}}}layout-section", f"{{{AC}}}layout-cell"):
        parts = [r for child in elem if (r := _node_to_md(child, ctx))]
        return "\n\n".join(filter(None, parts)) or None

    # ac:task-list — Confluence checklist → markdown checkboxes
    if tag == f"{{{AC}}}task-list":
        lines = []
        for task in elem:
            if task.tag != f"{{{AC}}}task":
                continue
            status_el = task.find(f"{{{AC}}}task-status")
            body_el = task.find(f"{{{AC}}}task-body")
            done = status_el is not None and (status_el.text or "").strip() == "complete"
            checkbox = "[x]" if done else "[ ]"
            body_text = _inline(body_el, ctx).strip() if body_el is not None else ""
            if body_text:
                first, *rest = body_text.splitlines()
                lines.append(f"- {checkbox} {first}")
                for line in rest:
                    lines.append(f"  {line}")
        return "\n".join(lines) if lines else None

    # Handle inline elements used at block level
    if tag in ("strong", "em", "code", "a", "span",
               f"{{{AC}}}link", f"{{{AC}}}inline-comment-marker"):
        return _inline_node(elem, ctx)

    # Unknown — preserve raw XML so content is not lost
    return _raw_xml(elem)


def _list_to_md(elem, ordered: bool, depth: int, ctx: _Ctx) -> str:
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
                inline_parts.append(_inline_node(child, ctx))
            if child.tail:
                inline_parts.append(child.tail)
        item_text = "".join(inline_parts).strip()
        bullet = f"{i}." if ordered else "-"
        lines.append(f"{prefix}{bullet} {item_text}")
        for nested_list in nested:
            nested_ordered = nested_list.tag == "ol"
            nested_md = _list_to_md(nested_list, ordered=nested_ordered, depth=depth + 1, ctx=ctx)
            lines.append(nested_md)
    return "\n".join(lines)


def _table_to_md(elem, ctx: _Ctx) -> str:
    for cell in elem.iter("th", "td"):
        if int(cell.get("rowspan", 1)) > 1 or int(cell.get("colspan", 1)) > 1:
            return _table_to_html(elem, ctx)

    rows = []
    # Find all tr elements (may be in tbody)
    for tr in elem.iter("tr"):
        cells = []
        is_header_row = False
        for cell in tr:
            if cell.tag == "th":
                is_header_row = True
                cells.append(_inline(cell, ctx).strip())
            elif cell.tag == "td":
                cells.append(_inline(cell, ctx).strip())
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


def _macro_to_md(elem, ctx: _Ctx) -> str:
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
        title = ""
        body_elem = None
        for child in elem:
            if child.tag == f"{{{AC}}}parameter" and child.get(f"{{{AC}}}name") == "title":
                title = (child.text or "").strip()
            elif child.tag == f"{{{AC}}}rich-text-body":
                body_elem = child
        title_suffix = f" {title}" if title else ""
        if body_elem is None:
            return f"> [!{keyword}]{title_suffix}"
        parts = []
        for child in body_elem:
            text = _node_to_md(child, ctx)
            if text:
                parts.append(text)
        if not parts:
            text = _inline(body_elem, ctx).strip()
            if text:
                parts.append(text)
        lines = [f"> [!{keyword}]{title_suffix}"]
        for part in parts:
            for line in part.splitlines():
                lines.append(f"> {line}")
        return "\n".join(lines)

    # section macro — layout container, flatten all column contents
    if name == "section":
        body_elem = elem.find(f"{{{AC}}}rich-text-body")
        if body_elem is None:
            return None
        parts = []
        for child in body_elem:
            result = _node_to_md(child, ctx)
            if result:
                parts.append(result)
        return "\n\n".join(filter(None, parts)) or None

    # column macro — render its rich-text-body
    if name == "column":
        body_elem = elem.find(f"{{{AC}}}rich-text-body")
        if body_elem is None:
            return None
        parts = []
        for child in body_elem:
            result = _node_to_md(child, ctx)
            if result:
                parts.append(result)
        return "\n\n".join(filter(None, parts)) or None

    # panel / details — styled box, render rich-text-body content
    if name in ("panel", "details"):
        body_elem = elem.find(f"{{{AC}}}rich-text-body")
        if body_elem is None:
            return None
        parts = [r for child in body_elem if (r := _node_to_md(child, ctx))]
        return "\n\n".join(filter(None, parts)) or None

    # aura-tab-collection — render each aura-tab as a section
    if name == "aura-tab-collection":
        body_elem = elem.find(f"{{{AC}}}rich-text-body")
        if body_elem is None:
            return None
        sections = []
        for child in body_elem:
            if child.tag == f"{{{AC}}}structured-macro" and child.get(f"{{{AC}}}name") == "aura-tab":
                tab_title = ""
                tab_body = None
                for sub in child:
                    if sub.tag == f"{{{AC}}}parameter" and sub.get(f"{{{AC}}}name") == "title":
                        tab_title = (sub.text or "").strip()
                    elif sub.tag == f"{{{AC}}}rich-text-body":
                        tab_body = sub
                parts = []
                if tab_body is not None:
                    parts = [r for c in tab_body if (r := _node_to_md(c, ctx))]
                body_text = "\n\n".join(filter(None, parts))
                if tab_title:
                    sections.append(f"#### {tab_title}\n\n{body_text}" if body_text else f"#### {tab_title}")
                elif body_text:
                    sections.append(body_text)
        return "\n\n".join(sections) or None

    # expand macro — collapsible block → <details><summary>
    if name == "expand":
        expand_title = ""
        body_elem = None
        for child in elem:
            if child.tag == f"{{{AC}}}parameter" and child.get(f"{{{AC}}}name") == "title":
                expand_title = (child.text or "").strip()
            elif child.tag == f"{{{AC}}}rich-text-body":
                body_elem = child
        parts = []
        if body_elem is not None:
            for child in body_elem:
                result = _node_to_md(child, ctx)
                if result:
                    parts.append(result)
        inner = "\n\n".join(filter(None, parts))
        summary = expand_title or "Details"
        return f"<details>\n<summary>{summary}</summary>\n\n{inner}\n\n</details>"

    # Unknown macro — preserve raw XML
    return _raw_xml(elem)
