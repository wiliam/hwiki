from hwiki._text import parse_page_id, parse_display_url


def test_raw_id():
    assert parse_page_id("123456") == "123456"


def test_viewpage_url():
    url = "https://confluence.example.com/pages/viewpage.action?pageId=98765"
    assert parse_page_id(url) == "98765"


def test_pages_path_url():
    url = "https://confluence.example.com/pages/98765"
    assert parse_page_id(url) == "98765"


def test_display_url_fallback():
    url = "https://confluence.example.com/display/ENG/My+Page"
    assert parse_page_id(url) == url


def test_already_id():
    assert parse_page_id("42") == "42"


def test_display_url_ascii():
    url = "https://wiki.example.com/display/ENG/My+Page"
    space, title = parse_display_url(url)
    assert space == "ENG"
    assert title == "My+Page"


def test_display_url_encoded():
    url = "https://wiki.example.com/display/WBS/%D0%A1%D1%82%D1%80%D0%B0%D0%BD%D0%B8%D1%86%D0%B0"
    space, title = parse_display_url(url)
    assert space == "WBS"
    assert title == "Страница"


def test_display_url_no_match():
    assert parse_display_url("https://wiki.example.com/pages/123") == ("", "")
