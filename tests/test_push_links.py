from hwiki._md_to_storage import md_to_storage


def test_local_link_to_ac_link():
    """./123-slug.md → ac:link when page_id in page_map."""
    page_map = {"123": ("My Page", "ENG")}
    md = "[See this](./123-my-page.md)"
    result = md_to_storage(md, page_map=page_map)
    assert "ri:page" in result
    assert 'ri:content-title="My Page"' in result
    assert "See this" in result


def test_local_link_different_slug_still_resolves():
    """ID prefix match — slug can be anything."""
    page_map = {"456": ("Other Title", "WBS")}
    md = "[text](./456-completely-different-slug.md)"
    result = md_to_storage(md, page_map=page_map)
    assert 'ri:content-title="Other Title"' in result


def test_local_link_unknown_page_falls_back():
    """If page_id not in page_map, emit normal <a href>."""
    md = "[text](./999-unknown.md)"
    result = md_to_storage(md, page_map={})
    assert "<a href" in result
    assert "999-unknown.md" in result


def test_external_link_unchanged():
    """External links are not affected by page_map."""
    md = "[Google](https://google.com)"
    result = md_to_storage(md, page_map={"123": ("X", "Y")})
    assert 'href="https://google.com"' in result


def test_no_page_map_backward_compatible():
    """Calling without page_map works as before."""
    md = "[Google](https://google.com)"
    result = md_to_storage(md)
    assert 'href="https://google.com"' in result
