"""One-off: replace the generated placeholder images with real Pexels photos.

Run:
    python -m scripts.fetch_pexels_images

Requires PEXELS_API_KEY in backend/.env (free key from pexels.com/api).
For each product, searches Pexels with a hand-picked query, downloads the
first landscape photo, saves it under static/uploads/pexels/<slug>.jpg, and
repoints that product's primary ProductImage at the new file.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.product import Product, ProductImage

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PEXELS_DIR = BACKEND_ROOT / settings.upload_dir / "pexels"
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

# Fictional brand/product names don't search well, so each slug maps to a
# generic, descriptive query instead.
SEARCH_QUERIES = {
    "rainbow-rise-wooden-block-set": "wooden building blocks toy",
    "magnatile-explorer-starter-pack": "magnetic tiles toy building",
    "gravity-loop-marble-run-deluxe": "marble run toy",
    "junior-engineer-nuts-bolts-workshop": "kids nuts and bolts toy tool set",
    "castle-quest-brick-set": "toy brick castle building set",
    "bramble-organic-cotton-bear": "teddy bear plush toy",
    "meadow-friends-rag-doll-iris": "rag doll toy",
    "little-kitchen-play-cafe-set": "wooden play kitchen toy",
    "dreamlight-nursery-doll-cot": "baby doll and cot toy",
    "pocket-pals-mini-plush-set": "mini plush animal toys",
    "woodland-match-memory-game": "memory matching card game",
    "sunny-farm-floor-puzzle": "farm floor puzzle kids",
    "rocket-race-family-board-game": "family board game",
    "story-cubes-adventure-dice": "story dice game",
    "deep-sea-200-piece-jigsaw": "ocean jigsaw puzzle",
    "trailblazer-wooden-balance-bike": "wooden balance bike kids",
    "backyard-bounce-jumbo-play-ball-set": "bouncy playground balls kids",
    "splash-zone-water-table": "kids water table outdoor",
    "sidewalk-chalk-artist-kit": "sidewalk chalk kids",
    "junior-archery-target-set": "kids archery set foam",
    "codebot-screen-free-coding-robot": "toy robot kids",
    "volcano-crystal-science-lab": "kids science kit experiment",
    "stargazer-beginner-telescope": "beginner telescope kids",
    "alphabet-adventure-magnetic-letters": "magnetic alphabet letters toy",
}


def fetch_photo_url(client: httpx.Client, query: str) -> str | None:
    """Return the first landscape-large photo URL Pexels finds for `query`."""
    response = client.get(
        PEXELS_SEARCH_URL,
        params={"query": query, "per_page": 1, "orientation": "landscape"},
    )
    response.raise_for_status()
    photos = response.json().get("photos", [])
    if not photos:
        return None
    return photos[0]["src"]["large"]


def main() -> None:
    load_dotenv(BACKEND_ROOT / ".env")
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("PEXELS_API_KEY is not set in backend/.env")

    PEXELS_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(headers={"Authorization": api_key}, timeout=20) as client, SessionLocal() as db:
        for slug, query in SEARCH_QUERIES.items():
            product = db.execute(
                select(Product).where(Product.slug == slug)
            ).scalar_one_or_none()
            if product is None:
                print(f"skip {slug}: product not found in DB")
                continue

            photo_url = fetch_photo_url(client, query)
            if photo_url is None:
                print(f"skip {slug}: no Pexels results for '{query}'")
                continue

            image_bytes = client.get(photo_url).content
            dest = PEXELS_DIR / f"{slug}.jpg"
            dest.write_bytes(image_bytes)

            relative_url = f"/{settings.upload_dir.strip('/')}/pexels/{slug}.jpg"
            primary = next((img for img in product.images if img.is_primary), None)
            if primary is None:
                primary = ProductImage(product_id=product.id, sort_order=0, is_primary=True)
                db.add(primary)
            primary.url = relative_url
            primary.alt_text = product.name

            print(f"ok   {slug} <- '{query}'")
            time.sleep(0.3)  # stay well under Pexels' rate limit

        db.commit()

    print(f"\nImages saved to {PEXELS_DIR}")


if __name__ == "__main__":
    main()
