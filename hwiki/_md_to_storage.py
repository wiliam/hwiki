from __future__ import annotations

import html
from markdown_it import MarkdownIt


_CALLOUT_TYPES = {"INFO", "WARNING", "NOTE", "TIP"}
_CALLOUT_TO_MACRO = {k: k.lower() for k in _CALLOUT_TYPES}


def md_to_storage(md: str) -> str:
    """Convert markdown to Confluence storage XHTML."""
    parser = MarkdownIt().enable("table")
    tokens = parser.parse(md)
    parts = _render_tokens(tokens)
    return "".join(parts)


def _render_tokens(tokens: list) -> list[str]:
    """Walk a flat token list and produce XHTML string fragments."""
    parts: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]

        # Headings
        if tok.type == "heading_open":
            level = tok.tag  # "h1" .. "h6"
            inline_tok = tokens[i + 1]
            content = _render_inline(inline_tok.children or [])
            parts.append(f"<{level}>{content}</{level}>")
            i += 3  # heading_open, inline, heading_close
            continue

        # Paragraph
        if tok.type == "paragraph_open":
            inline_tok = tokens[i + 1]
            content = _render_inline(inline_tok.children or [])
            parts.append(f"<p>{content}</p>")
            i += 3
            continue

        # Horizontal rule
        if tok.type == "hr":
            parts.append("<hr/>")
            i += 1
            continue

        # Fenced code block
        if tok.type == "fence":
            lang = html.escape(tok.info.strip()) if tok.info else ""
            code = tok.content  # not escaped — goes into CDATA
            parts.append(
                f'<ac:structured-macro ac:name="code">'
                f'<ac:parameter ac:name="language">{lang}</ac:parameter>'
                f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
                f'</ac:structured-macro>'
            )
            i += 1
            continue

        # Code block (indented)
        if tok.type == "code_block":
            code = tok.content
            parts.append(
                f'<ac:structured-macro ac:name="code">'
                f'<ac:parameter ac:name="language"></ac:parameter>'
                f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
                f'</ac:structured-macro>'
            )
            i += 1
            continue

        # Bullet list
        if tok.type == "bullet_list_open":
            end_idx, list_html = _render_list(tokens, i, "ul")
            parts.append(list_html)
            i = end_idx + 1
            continue

        # Ordered list
        if tok.type == "ordered_list_open":
            end_idx, list_html = _render_list(tokens, i, "ol")
            parts.append(list_html)
            i = end_idx + 1
            continue

        # Blockquote
        if tok.type == "blockquote_open":
            end_idx, bq_html = _render_blockquote(tokens, i)
            parts.append(bq_html)
            i = end_idx + 1
            continue

        # Table
        if tok.type == "table_open":
            end_idx, table_html = _render_table(tokens, i)
            parts.append(table_html)
            i = end_idx + 1
            continue

        i += 1

    return parts


def _render_inline(children: list) -> str:
    """Render a list of inline tokens to an HTML/XHTML string."""
    parts = []
    i = 0
    while i < len(children):
        tok = children[i]

        if tok.type == "text":
            parts.append(html.escape(tok.content))
        elif tok.type == "softbreak":
            parts.append(" ")
        elif tok.type == "hardbreak":
            parts.append("<br/>")
        elif tok.type == "strong_open":
            # Collect until strong_close
            inner, i = _collect_until(children, i + 1, "strong_close")
            parts.append(f"<strong>{inner}</strong>")
            i += 1
            continue
        elif tok.type == "em_open":
            inner, i = _collect_until(children, i + 1, "em_close")
            parts.append(f"<em>{inner}</em>")
            i += 1
            continue
        elif tok.type == "code_inline":
            parts.append(f"<code>{html.escape(tok.content)}</code>")
        elif tok.type == "link_open":
            attrs = tok.attrs or {}
            href = attrs.get("href", "") if isinstance(attrs, dict) else ""
            inner, i = _collect_until(children, i + 1, "link_close")
            parts.append(f'<a href="{html.escape(href)}">{inner}</a>')
            i += 1
            continue
        elif tok.type == "image":
            attrs = tok.attrs or {}
            src = attrs.get("src", "") if isinstance(attrs, dict) else ""
            alt = tok.content or ""
            parts.append(
                f'<ac:image><ri:url ri:value="{html.escape(src)}"/></ac:image>'
            )
        elif tok.type in ("strong_close", "em_close", "link_close"):
            # Should be consumed above; skip defensively
            pass

        i += 1

    return "".join(parts)


def _collect_until(children: list, start: int, end_type: str) -> tuple[str, int]:
    """Collect inline tokens from start until end_type, return (html, end_index)."""
    sub = []
    i = start
    while i < len(children):
        if children[i].type == end_type:
            return _render_inline(sub), i
        sub.append(children[i])
        i += 1
    return _render_inline(sub), i


def _render_list(tokens: list, start: int, tag: str) -> tuple[int, str]:
    """Render a bullet_list or ordered_list. Returns (end_index, html)."""
    close_type = f"{'bullet' if tag == 'ul' else 'ordered'}_list_close"
    parts = []
    i = start + 1
    depth = 1

    while i < len(tokens):
        tok = tokens[i]
        if tok.type in ("bullet_list_open", "ordered_list_open"):
            depth += 1
        if tok.type in ("bullet_list_close", "ordered_list_close"):
            depth -= 1
            if depth == 0:
                break

        if tok.type == "list_item_open" and depth == 1:
            end_li, li_html = _render_list_item(tokens, i)
            parts.append(f"<li>{li_html}</li>")
            i = end_li
        else:
            i += 1

    return i, f"<{tag}>{''.join(parts)}</{tag}>"


def _render_list_item(tokens: list, start: int) -> tuple[int, str]:
    """Render content of a list_item_open..list_item_close. Returns (end_index, html)."""
    parts = []
    i = start + 1
    depth = 1

    while i < len(tokens):
        tok = tokens[i]

        if tok.type == "list_item_open":
            depth += 1
        if tok.type == "list_item_close":
            depth -= 1
            if depth == 0:
                break

        if depth == 1:
            if tok.type == "paragraph_open":
                inline_tok = tokens[i + 1]
                content = _render_inline(inline_tok.children or [])
                parts.append(content)
                i += 3
                continue
            elif tok.type == "inline":
                parts.append(_render_inline(tok.children or []))
            elif tok.type == "bullet_list_open":
                end_idx, list_html = _render_list(tokens, i, "ul")
                parts.append(list_html)
                i = end_idx + 1
                continue
            elif tok.type == "ordered_list_open":
                end_idx, list_html = _render_list(tokens, i, "ol")
                parts.append(list_html)
                i = end_idx + 1
                continue

        i += 1

    return i, "".join(parts)


def _render_blockquote(tokens: list, start: int) -> tuple[int, str]:
    """Render blockquote_open..blockquote_close. Detects callout syntax."""
    inner_tokens = []
    i = start + 1
    depth = 1

    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "blockquote_open":
            depth += 1
        if tok.type == "blockquote_close":
            depth -= 1
            if depth == 0:
                break
        if depth == 1:
            inner_tokens.append(tok)
        i += 1

    end_idx = i

    # Check if this is a callout: first paragraph starts with [!TYPE]
    callout_type = _detect_callout(inner_tokens)
    if callout_type:
        macro_name = _CALLOUT_TO_MACRO[callout_type]
        # Get the paragraph content after the [!TYPE] marker
        body_html = _render_callout_body(inner_tokens, callout_type)
        result = (
            f'<ac:structured-macro ac:name="{macro_name}">'
            f'<ac:rich-text-body>{body_html}</ac:rich-text-body>'
            f'</ac:structured-macro>'
        )
        return end_idx, result

    # Regular blockquote
    inner_parts = _render_tokens(inner_tokens)
    return end_idx, f"<blockquote>{''.join(inner_parts)}</blockquote>"


def _detect_callout(tokens: list) -> str | None:
    """Check if token stream starts with a callout marker like [!INFO]. Return type or None."""
    for tok in tokens:
        if tok.type == "paragraph_open":
            continue
        if tok.type == "inline":
            text = tok.content.strip()
            if text.startswith("[!") and "]" in text:
                marker = text[2:text.index("]")]
                if marker in _CALLOUT_TYPES:
                    return marker
            return None
        if tok.type == "paragraph_close":
            return None
    return None


def _render_callout_body(tokens: list, callout_type: str) -> str:
    """Render the body of a callout macro, skipping the [!TYPE] line."""
    parts = []
    skip_first_para = True
    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if skip_first_para and tok.type == "paragraph_open":
            # Find the inline token and skip if it only has the marker
            inline_tok = tokens[i + 1] if i + 1 < len(tokens) else None
            if inline_tok and inline_tok.type == "inline":
                content = inline_tok.content.strip()
                marker = f"[!{callout_type}]"
                if content.startswith(marker):
                    remaining = content[len(marker):].strip()
                    if remaining:
                        parts.append(f"<p>{html.escape(remaining)}</p>")
                    skip_first_para = False
                    i += 3  # skip paragraph_open, inline, paragraph_close
                    continue
            skip_first_para = False

        if tok.type == "paragraph_open":
            inline_tok = tokens[i + 1] if i + 1 < len(tokens) else None
            if inline_tok and inline_tok.type == "inline":
                content = _render_inline(inline_tok.children or [])
                parts.append(f"<p>{content}</p>")
            i += 3
            continue

        i += 1

    return "".join(parts)


def _render_table(tokens: list, start: int) -> tuple[int, str]:
    """Render table_open..table_close."""
    i = start + 1
    depth = 1
    rows = []
    current_row: list[tuple[str, str]] = []  # list of (tag, content)
    in_cell = False
    cell_tag = "td"
    cell_tokens: list = []

    while i < len(tokens):
        tok = tokens[i]

        if tok.type == "table_open":
            depth += 1
        if tok.type == "table_close":
            depth -= 1
            if depth == 0:
                break

        if tok.type == "tr_open":
            current_row = []
        elif tok.type == "tr_close":
            rows.append(current_row)
        elif tok.type == "th_open":
            in_cell = True
            cell_tag = "th"
            cell_tokens = []
        elif tok.type == "td_open":
            in_cell = True
            cell_tag = "td"
            cell_tokens = []
        elif tok.type in ("th_close", "td_close"):
            if in_cell:
                content = _render_inline(
                    cell_tokens[0].children if cell_tokens else []
                )
                current_row.append((cell_tag, content))
                in_cell = False
                cell_tokens = []
        elif tok.type == "inline" and in_cell:
            cell_tokens.append(tok)

        i += 1

    # Build table HTML
    html_parts = ["<table><tbody>"]
    for row in rows:
        html_parts.append("<tr>")
        for tag, content in row:
            html_parts.append(f"<{tag}>{content}</{tag}>")
        html_parts.append("</tr>")
    html_parts.append("</tbody></table>")

    return i, "".join(html_parts)
