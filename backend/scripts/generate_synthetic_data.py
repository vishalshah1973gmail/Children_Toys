"""Generate synthetic 2026 customer and purchase data for the toy store.

Writes five CSV files into backend/data/:

    products.csv      the 24 catalogue toys, for reference and analysis
    customers.csv     50 synthetic customers with signup dates and locations
    orders.csv        ~200 orders spread across January-December 2026
    order_items.csv   the line items belonging to those orders
    payments.csv      one payment row per non-cancelled order

The generator is deterministic: the same RANDOM_SEED always produces the same
dataset, so numbers quoted in a report stay true after a regeneration.

Run:  python -m scripts.generate_synthetic_data
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

from scripts.catalog_data import CATEGORIES, PRODUCTS

RANDOM_SEED = 2026
YEAR = 2026
NUM_CUSTOMERS = 50
NUM_ORDERS = 200

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# Purchase volume by month. Toy retail is back-loaded: a quiet spring, a
# back-to-school bump in August, and a heavy November-December run-up.
MONTH_WEIGHTS = {
    1: 0.9, 2: 0.7, 3: 0.7, 4: 0.8, 5: 0.9, 6: 1.0,
    7: 1.0, 8: 1.2, 9: 0.9, 10: 1.1, 11: 1.8, 12: 2.4,
}

FIRST_NAMES = [
    "Aarav", "Amelia", "Priya", "Noah", "Sofia", "Liam", "Mia", "Ethan", "Isla",
    "Rohan", "Chloe", "Mateo", "Ava", "Daniel", "Nina", "Omar", "Grace", "Leo",
    "Zoe", "Hassan", "Elena", "Marcus", "Ruby", "Kai", "Farah", "Jonah", "Lena",
    "Diego", "Anaya", "Theo", "Hana", "Caleb", "Maya", "Ivan", "Talia", "Owen",
    "Nadia", "Felix", "Sana", "Julian", "Iris", "Arjun", "Clara", "Emeka", "Yuki",
    "Rosa", "Dmitri", "Layla", "Andre", "Freya",
]
LAST_NAMES = [
    "Shah", "Nguyen", "Patel", "Rivera", "Okafor", "Kim", "Bennett", "Silva",
    "Kowalski", "Haddad", "Larsen", "Mehta", "Brooks", "Ferreira", "Novak",
    "Castillo", "Ahmed", "Fischer", "Dubois", "Romano", "Petrov", "Byrne",
    "Sandoval", "Adeyemi", "Tanaka", "Weber", "Moreau", "Grant", "Iqbal", "Lund",
]
CITIES = [
    ("Sayreville", "NJ", "08872"), ("Edison", "NJ", "08817"),
    ("Princeton", "NJ", "08540"), ("Jersey City", "NJ", "07302"),
    ("Brooklyn", "NY", "11215"), ("Queens", "NY", "11375"),
    ("Stamford", "CT", "06902"), ("Philadelphia", "PA", "19103"),
    ("Boston", "MA", "02116"), ("Alexandria", "VA", "22314"),
    ("Columbus", "OH", "43215"), ("Austin", "TX", "78704"),
    ("Denver", "CO", "80203"), ("Seattle", "WA", "98109"),
    ("Chicago", "IL", "60614"),
]
STREETS = [
    "Maple Ave", "Ernston Rd", "Washington St", "Cedar Ln", "Bordentown Ave",
    "Park Pl", "Highland Blvd", "Willow Way", "Orchard St", "Franklin Ave",
]
CHANNELS = ["organic_search", "email", "paid_social", "direct", "referral"]

SHIPPING_FLAT_CENTS = 599
FREE_SHIPPING_THRESHOLD_CENTS = 5000
TAX_RATE_BPS = 663


def _tax(subtotal: int) -> int:
    return (subtotal * TAX_RATE_BPS + 5_000) // 10_000


def _shipping(subtotal: int) -> int:
    return 0 if subtotal >= FREE_SHIPPING_THRESHOLD_CENTS else SHIPPING_FLAT_CENTS


def _weighted_2026_date(rng: random.Random) -> date:
    """Pick a date in 2026 weighted by the seasonality table."""
    months = list(MONTH_WEIGHTS)
    month = rng.choices(months, weights=[MONTH_WEIGHTS[m] for m in months], k=1)[0]
    if month == 12:
        last_day = 31
    else:
        last_day = (date(YEAR, month + 1, 1) - timedelta(days=1)).day
    return date(YEAR, month, rng.randint(1, last_day))


def build_customers(rng: random.Random) -> List[Dict]:
    """Fifty synthetic customers, each with a signup date and address."""
    customers: List[Dict] = []
    used_usernames: set[str] = set()

    for index in range(1, NUM_CUSTOMERS + 1):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        base_username = f"{first.lower()}.{last.lower()}"
        username = base_username
        suffix = 2
        while username in used_usernames:
            username = f"{base_username}{suffix}"
            suffix += 1
        used_usernames.add(username)

        city, state, postal = rng.choice(CITIES)
        # Roughly a fifth of the base signed up before 2026.
        if rng.random() < 0.2:
            signup = date(2025, rng.randint(6, 12), rng.randint(1, 28))
        else:
            signup = date(YEAR, rng.randint(1, 11), rng.randint(1, 28))

        customers.append(
            {
                "customer_id": index,
                "username": username,
                "email": f"{username}@example.com",
                "full_name": f"{first} {last}",
                "signup_date": signup.isoformat(),
                "city": city,
                "state": state,
                "postal_code": postal,
                "address_line1": f"{rng.randint(12, 980)} {rng.choice(STREETS)}",
                "children_count": rng.choices([1, 2, 3], weights=[0.5, 0.38, 0.12])[0],
                "youngest_child_age_months": rng.randint(6, 132),
                "acquisition_channel": rng.choices(
                    CHANNELS, weights=[0.32, 0.22, 0.2, 0.16, 0.10]
                )[0],
                "marketing_opt_in": rng.random() < 0.62,
            }
        )
    return customers


def build_orders(rng: random.Random, customers: List[Dict]) -> tuple[list, list, list]:
    """Generate orders, their line items and their payments."""
    products_by_slug = {product["slug"]: product for product in PRODUCTS}
    slugs = list(products_by_slug)

    # A popularity curve: a few toys carry a disproportionate share of orders.
    popularity = {}
    for rank, slug in enumerate(rng.sample(slugs, len(slugs))):
        popularity[slug] = 1.0 / (rank + 3) ** 0.7
    for product in PRODUCTS:
        if product["is_featured"]:
            popularity[product["slug"]] *= 2.2

    weights = [popularity[slug] for slug in slugs]

    # Repeat buyers: weight customers so ~30% of them place multiple orders.
    customer_weights = [
        rng.choices([1.0, 2.5, 5.0], weights=[0.55, 0.30, 0.15])[0] for _ in customers
    ]

    orders: List[Dict] = []
    items: List[Dict] = []
    payments: List[Dict] = []
    item_id = 0
    today = date(YEAR, 9, 6)

    for sequence in range(1, NUM_ORDERS + 1):
        customer = rng.choices(customers, weights=customer_weights, k=1)[0]
        signup = date.fromisoformat(customer["signup_date"])
        placed = _weighted_2026_date(rng)
        # An order cannot precede the account that placed it.
        if placed < signup:
            placed = min(signup + timedelta(days=rng.randint(0, 45)), date(YEAR, 12, 31))

        line_count = rng.choices([1, 2, 3, 4], weights=[0.42, 0.32, 0.18, 0.08])[0]
        chosen = set()
        while len(chosen) < line_count:
            chosen.add(rng.choices(slugs, weights=weights, k=1)[0])

        subtotal = 0
        order_lines = []
        for slug in chosen:
            product = products_by_slug[slug]
            quantity = rng.choices([1, 2, 3], weights=[0.78, 0.18, 0.04])[0]
            line_total = product["price_cents"] * quantity
            subtotal += line_total
            item_id += 1
            order_lines.append(
                {
                    "order_item_id": item_id,
                    "order_number": "",
                    "product_slug": slug,
                    "product_name": product["name"],
                    "category_slug": product["category_slug"],
                    "brand": product["brand"],
                    "unit_price_cents": product["price_cents"],
                    "quantity": quantity,
                    "line_total_cents": line_total,
                }
            )

        shipping = _shipping(subtotal)
        tax = _tax(subtotal)
        total = subtotal + shipping + tax
        order_number = f"TB-{placed.strftime('%Y%m%d')}-{sequence:04d}"

        age_days = (today - placed).days
        roll = rng.random()
        if roll < 0.04:
            status = "cancelled"
        elif age_days > 21:
            status = "delivered"
        elif age_days > 7:
            status = "shipped"
        elif age_days >= 0:
            status = "paid"
        else:
            # Dated later in 2026 than "today": treat as booked and paid.
            status = "paid"

        placed_at = datetime(
            placed.year, placed.month, placed.day,
            rng.randint(7, 22), rng.randint(0, 59), tzinfo=timezone.utc,
        )
        paid_at = placed_at + timedelta(minutes=rng.randint(1, 25))
        shipped_at = paid_at + timedelta(days=rng.randint(1, 3)) if status in {"shipped", "delivered"} else None
        delivered_at = shipped_at + timedelta(days=rng.randint(1, 5)) if status == "delivered" and shipped_at else None

        for line in order_lines:
            line["order_number"] = order_number
        items.extend(order_lines)

        orders.append(
            {
                "order_number": order_number,
                "customer_id": customer["customer_id"],
                "customer_username": customer["username"],
                "status": status,
                "placed_at": placed_at.isoformat(),
                "paid_at": "" if status == "cancelled" else paid_at.isoformat(),
                "shipped_at": shipped_at.isoformat() if shipped_at else "",
                "delivered_at": delivered_at.isoformat() if delivered_at else "",
                "item_count": sum(line["quantity"] for line in order_lines),
                "subtotal_cents": subtotal,
                "shipping_cents": shipping,
                "tax_cents": tax,
                "total_cents": total,
                "currency": "usd",
                "channel": customer["acquisition_channel"],
                "shipping_city": customer["city"],
                "shipping_state": customer["state"],
                "shipping_postal_code": customer["postal_code"],
            }
        )

        if status != "cancelled":
            payments.append(
                {
                    "payment_id": len(payments) + 1,
                    "order_number": order_number,
                    "provider": "stripe",
                    "stripe_payment_intent_id": f"pi_test_{rng.getrandbits(48):012x}",
                    "amount_cents": total,
                    "currency": "usd",
                    "status": "succeeded",
                    "created_at": paid_at.isoformat(),
                }
            )

    orders.sort(key=lambda row: row["placed_at"])
    return orders, items, payments


def _write_csv(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def generate(output_dir: Path = DATA_DIR, seed: int = RANDOM_SEED) -> Dict[str, Path]:
    """Generate every CSV and return a map of name -> path."""
    rng = random.Random(seed)
    customers = build_customers(rng)
    orders, items, payments = build_orders(rng, customers)

    category_names = {category["slug"]: category["name"] for category in CATEGORIES}
    product_rows = [
        {
            "product_slug": product["slug"],
            "product_name": product["name"],
            "category_slug": product["category_slug"],
            "category_name": category_names[product["category_slug"]],
            "brand": product["brand"],
            "price_cents": product["price_cents"],
            "price_usd": f"{product['price_cents'] / 100:.2f}",
            "stock_quantity": product["stock_quantity"],
            "min_age_months": product["min_age_months"],
            "max_age_months": product["max_age_months"],
            "is_featured": product["is_featured"],
        }
        for product in PRODUCTS
    ]

    paths = {
        "products": output_dir / "products.csv",
        "customers": output_dir / "customers.csv",
        "orders": output_dir / "orders.csv",
        "order_items": output_dir / "order_items.csv",
        "payments": output_dir / "payments.csv",
    }
    _write_csv(paths["products"], product_rows)
    _write_csv(paths["customers"], customers)
    _write_csv(paths["orders"], orders)
    _write_csv(paths["order_items"], items)
    _write_csv(paths["payments"], payments)

    revenue = sum(order["total_cents"] for order in orders if order["status"] != "cancelled")
    print(f"Customers      : {len(customers)}")
    print(f"Orders         : {len(orders)}")
    print(f"Order items    : {len(items)}")
    print(f"Payments       : {len(payments)}")
    print(f"2026 revenue   : ${revenue / 100:,.2f}")
    print(f"Written to     : {output_dir}")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic 2026 toy-store data.")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed")
    parser.add_argument("--out", type=Path, default=DATA_DIR, help="Output directory")
    args = parser.parse_args()
    generate(args.out, args.seed)


if __name__ == "__main__":
    main()
