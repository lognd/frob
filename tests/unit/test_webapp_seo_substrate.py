"""frob.webapp._seo_substrate coverage: positive/negative extraction controls.

frob:ticket T-5364
"""

from __future__ import annotations

from pathlib import Path

from frob.webapp._seo_substrate import (
    SeoError,
    build_duplicate_title_index,
    extract_page_metadata,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "seo1xx" / "routes"
)


# frob:tests src/frob/webapp/_seo_substrate.py::extract_page_metadata kind="unit"
# frob:tests src/frob/webapp/_seo_substrate.py::PageMetadata kind="unit"
# frob:tests src/frob/webapp/_seo_substrate.py::LinkTag kind="unit"
# frob:tests src/frob/webapp/_seo_substrate.py::MetaTag kind="unit"
def test_extract_page_metadata_html_positive_control():
    """MUST-FIRE: an HTML route's <head> yields title/meta/link/json-ld."""
    result = extract_page_metadata(_FIXTURE_ROOT / "home.html", route="/")
    assert result.is_ok
    page = result.danger_ok
    assert page.route == "/"
    assert page.title == "Acme Storefront"
    assert any(
        m.name == "description" and m.content == "Buy widgets at Acme"
        for m in page.meta
    )
    assert any(m.property == "og:title" for m in page.meta)
    assert any(
        link.rel == "canonical" and link.href == "https://acme.example/"
        for link in page.links
    )
    assert len(page.json_ld) == 1
    assert "Organization" in page.json_ld[0]


# frob:tests src/frob/webapp/_seo_substrate.py::extract_page_metadata kind="unit"
def test_extract_page_metadata_jsx_positive_control():
    """MUST-FIRE: a JSX <Head> wrapper route yields the same normalized shape."""
    result = extract_page_metadata(_FIXTURE_ROOT / "product.jsx", route="/product")
    assert result.is_ok
    page = result.danger_ok
    assert page.title == "Widget Pro"
    assert any(m.name == "description" for m in page.meta)
    assert any(link.rel == "canonical" for link in page.links)
    assert len(page.json_ld) == 1


# frob:tests src/frob/webapp/_seo_substrate.py::extract_page_metadata kind="unit"
# frob:tests src/frob/webapp/_seo_substrate.py::SeoError kind="unit"
def test_extract_page_metadata_no_head_html_is_negative_control():
    """MUST-FIRE (negative control): an HTML file with no <head> element errors NoHeadElement."""
    result = extract_page_metadata(_FIXTURE_ROOT / "no_head.html")
    assert result.is_err
    assert result.danger_err is SeoError.NoHeadElement


# frob:tests src/frob/webapp/_seo_substrate.py::extract_page_metadata kind="unit"
def test_extract_page_metadata_no_head_jsx_is_negative_control():
    """MUST-FIRE (negative control): a JSX file with no Head wrapper errors NoHeadElement."""
    result = extract_page_metadata(_FIXTURE_ROOT / "no_head.jsx")
    assert result.is_err
    assert result.danger_err is SeoError.NoHeadElement


# frob:tests src/frob/webapp/_seo_substrate.py::extract_page_metadata kind="unit"
def test_extract_page_metadata_unsupported_extension_is_negative_control():
    """MUST-FIRE (negative control): a non-.html/.jsx path errors UnsupportedLanguage."""
    result = extract_page_metadata(_FIXTURE_ROOT.parent / "vue" / "does_not_exist.vue")
    assert result.is_err
    assert result.danger_err is SeoError.UnsupportedLanguage


# frob:tests src/frob/webapp/_seo_substrate.py::build_duplicate_title_index kind="unit"
def test_build_duplicate_title_index_positive_control():
    """MUST-FIRE: the planted duplicate-title pair (home.html/duplicate.html) is reported."""
    pages = tuple(
        extract_page_metadata(_FIXTURE_ROOT / name, route=route).danger_ok
        for name, route in (
            ("home.html", "/"),
            ("about.html", "/about"),
            ("duplicate.html", "/dup"),
        )
    )
    index = build_duplicate_title_index(pages)
    assert index == {"Acme Storefront": ("/", "/dup")}


# frob:tests src/frob/webapp/_seo_substrate.py::build_duplicate_title_index kind="unit"
def test_build_duplicate_title_index_no_duplicates_is_negative_control():
    """MUST-FIRE (negative control): distinct titles produce an empty index."""
    pages = tuple(
        extract_page_metadata(_FIXTURE_ROOT / name, route=route).danger_ok
        for name, route in (("home.html", "/"), ("about.html", "/about"))
    )
    assert build_duplicate_title_index(pages) == {}
