from hwiki._text import parse_page_id


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
