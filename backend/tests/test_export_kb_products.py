"""Tests for the knowledge-base product export."""

from scripts.export_kb_products import render_products_markdown


def test_formats_price_and_includes_url(product_factory):
    product = product_factory(slug="red-ball", price_cents=1999, stock=5)
    text = render_products_markdown([product], "2026-10-04", "http://localhost:5173")
    assert "$19.99" in text
    assert "http://localhost:5173/product/red-ball" in text
    assert "Snapshot as of 2026-10-04" in text


def test_whole_dollar_price_has_two_decimals(product_factory):
    product = product_factory(slug="blocks", price_cents=500)
    assert "$5.00" in render_products_markdown([product], "2026-10-04", "http://x")


def test_out_of_stock_is_labelled(product_factory):
    product = product_factory(slug="sold-out", stock=0)
    assert "Out of stock" in render_products_markdown([product], "2026-10-04", "http://x")


def test_inactive_product_is_excluded(db, product_factory):
    product = product_factory(slug="hidden")
    product.is_active = False
    db.commit()
    text = render_products_markdown([product], "2026-10-04", "http://x")
    assert "Hidden" not in text


def test_empty_catalogue_still_valid(db):
    text = render_products_markdown([], "2026-10-04", "http://x")
    assert text.startswith("# ToyBox Product Catalogue")
    assert "No products are currently listed." in text
