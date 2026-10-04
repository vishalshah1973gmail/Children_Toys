"""Tests for matching product names inside chat replies."""

from app.services.chat_products import MAX_PRODUCT_CARDS, find_mentioned_products


def _product(db, product_factory, slug, name, **kwargs):
    product = product_factory(slug=slug, **kwargs)
    product.name = name
    db.commit()
    return product


def _ids(products):
    return [product.id for product in products]


def test_matches_full_name(db, product_factory):
    product = _product(db, product_factory, "rocket-race", "Rocket Race Family Board Game")
    found = find_mentioned_products(db, "Try the Rocket Race Family Board Game today!")
    assert _ids(found) == [product.id]


def test_matches_name_without_parenthetical(db, product_factory):
    product = _product(
        db, product_factory, "rainbow-rise", "Rainbow Rise Wooden Block Set (100 pieces)"
    )
    found = find_mentioned_products(db, "The Rainbow Rise Wooden Block Set is lovely.")
    assert _ids(found) == [product.id]


def test_matching_ignores_letter_case(db, product_factory):
    product = _product(db, product_factory, "rocket-race", "Rocket Race Family Board Game")
    found = find_mentioned_products(db, "ROCKET RACE FAMILY BOARD GAME is popular")
    assert _ids(found) == [product.id]


def test_curly_apostrophe_matches_straight(db, product_factory):
    product = _product(db, product_factory, "explorer-tent", "Explorer's Camping Tent Set")
    found = find_mentioned_products(db, "Take the Explorer's Camping Tent Set outside.")
    assert _ids(found) == [product.id]


def test_caps_results_and_orders_by_first_appearance(db, product_factory):
    names = ["Alpha Puzzle Box", "Bravo Puzzle Box", "Charlie Puzzle Box", "Delta Puzzle Box"]
    products = {
        name.split()[0]: _product(db, product_factory, f"p-{index}", name)
        for index, name in enumerate(names)
    }
    reply = "Delta Puzzle Box, then Bravo Puzzle Box, Charlie Puzzle Box and Alpha Puzzle Box."
    found = find_mentioned_products(db, reply)
    assert len(found) == MAX_PRODUCT_CARDS == 3
    assert _ids(found) == [
        products["Delta"].id,
        products["Bravo"].id,
        products["Charlie"].id,
    ]


def test_same_product_named_twice_appears_once(db, product_factory):
    product = _product(db, product_factory, "castle-quest", "Castle Quest Brick Set")
    found = find_mentioned_products(
        db, "Castle Quest Brick Set is great. Again: Castle Quest Brick Set!"
    )
    assert _ids(found) == [product.id]


def test_longer_name_wins_over_contained_name(db, product_factory):
    plain = _product(db, product_factory, "marble-plain", "Marble Run Set")
    deluxe = _product(db, product_factory, "marble-deluxe", "Marble Run Set Deluxe")
    assert _ids(find_mentioned_products(db, "The Marble Run Set Deluxe is great")) == [deluxe.id]
    assert _ids(find_mentioned_products(db, "The Marble Run Set is great")) == [plain.id]


def test_partial_word_does_not_match(db, product_factory):
    _product(db, product_factory, "rocket-race", "Rocket Race Game")
    assert find_mentioned_products(db, "We stock Rocket Race Games too") == []


def test_inactive_product_excluded(db, product_factory):
    product = _product(db, product_factory, "retired", "Retired Wooden Train")
    product.is_active = False
    db.commit()
    assert find_mentioned_products(db, "The Retired Wooden Train is gone") == []


def test_out_of_stock_product_is_included(db, product_factory):
    product = _product(db, product_factory, "sold-out", "Sold Out Robot Kit", stock=0)
    found = find_mentioned_products(db, "The Sold Out Robot Kit is popular")
    assert _ids(found) == [product.id]


def test_no_match_returns_empty_list(db, product_factory):
    _product(db, product_factory, "rocket-race", "Rocket Race Family Board Game")
    assert find_mentioned_products(db, "Shipping is $5.99.") == []


def test_very_short_names_are_ignored(db, product_factory):
    _product(db, product_factory, "ball", "Ball")
    assert find_mentioned_products(db, "Ball") == []
