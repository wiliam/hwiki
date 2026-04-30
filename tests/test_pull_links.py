from hwiki._storage_to_md import storage_to_md

AC = "http://www.atlassian.com/schema/confluence/4/ac/"
RI = "http://www.atlassian.com/schema/confluence/4/ri/"


def _ac_page_link(title, space, text):
    """Build a minimal ac:link storage fragment."""
    return (
        f'<ac:link xmlns:ac="{AC}" xmlns:ri="{RI}">'
        f'<ri:page ri:content-title="{title}" ri:space-key="{space}"/>'
        f'<ac:plain-text-link-body><![CDATA[{text}]]></ac:plain-text-link-body>'
        f'</ac:link>'
    )


def test_internal_link_becomes_local_path():
    """When page is in link_map, ac:link → ./id-slug.md."""
    xhtml = f"<p>{_ac_page_link('My Page', 'ENG', 'See this')}</p>"
    link_map = {"999": "999-my-page.md"}
    title_index = {("ENG", "My Page"): "999"}
    result = storage_to_md(xhtml, host="https://wiki.example.com", space_key="ENG",
                           link_map=link_map, title_index=title_index)
    assert "[See this](./999-my-page.md)" in result


def test_external_link_stays_wiki_url():
    """When page is NOT in link_map, ac:link → display URL."""
    xhtml = f"<p>{_ac_page_link('Other Page', 'OTHER', 'click')}</p>"
    result = storage_to_md(xhtml, host="https://wiki.example.com", space_key="ENG",
                           link_map={}, title_index={})
    assert "[click](https://wiki.example.com/display/OTHER/" in result


def test_no_link_map_same_as_before():
    """Without link_map, behavior is identical to pre-sync (wiki URL)."""
    xhtml = f"<p>{_ac_page_link('Some Page', 'ENG', 'text')}</p>"
    result_before = storage_to_md(xhtml, host="https://wiki.example.com", space_key="ENG")
    result_after = storage_to_md(xhtml, host="https://wiki.example.com", space_key="ENG",
                                 link_map={}, title_index={})
    assert result_before == result_after


def test_attachment_image_url():
    """ri:attachment images use host/download/attachments/page_id/filename."""
    xhtml = (
        f'<ac:image xmlns:ac="{AC}" xmlns:ri="{RI}">'
        f'<ri:attachment ri:filename="photo.png"/>'
        f'</ac:image>'
    )
    result = storage_to_md(xhtml, host="https://wiki.example.com", page_id="123")
    assert "https://wiki.example.com/download/attachments/123/photo.png" in result
