"""Static catalog content shared by the seed script and the data generator.

Five categories and twenty-four toys. Prices are integer cents, ages are in
months so that "18 months" and "8 years" live on one scale.
"""

CATEGORIES = [
    {
        "name": "Building & Construction",
        "slug": "building-construction",
        "description": "Blocks, bricks, magnetic tiles and marble runs for small engineers.",
    },
    {
        "name": "Dolls & Plush",
        "slug": "dolls-plush",
        "description": "Soft companions, dolls and playsets for imaginative and comfort play.",
    },
    {
        "name": "Games & Puzzles",
        "slug": "games-puzzles",
        "description": "Board games, card games and jigsaws for the whole family table.",
    },
    {
        "name": "Outdoor & Active Play",
        "slug": "outdoor-active-play",
        "description": "Ride-ons, sports sets and backyard toys that burn off the afternoon.",
    },
    {
        "name": "STEM & Learning",
        "slug": "stem-learning",
        "description": "Science kits, coding robots and early-literacy toys that teach while they play.",
    },
]

SAFETY_SMALL_PARTS = (
    "Choking hazard: contains small parts. Not for children under 3 years. "
    "Adult supervision recommended."
)
SAFETY_INFANT = (
    "Tested to ASTM F963. No small parts. Surface-wash only. "
    "Inspect for wear before each use."
)
SAFETY_OUTDOOR = (
    "Wear a properly fitted helmet and protective gear. Use on flat, dry surfaces "
    "away from traffic. Adult supervision required."
)
SAFETY_ELECTRONIC = (
    "Contains button-cell batteries; keep the battery compartment screwed shut and "
    "away from children under 3. Swallowing a battery is a medical emergency."
)

PRODUCTS = [
    # --- Building & Construction ------------------------------------------
    {
        "name": "Rainbow Rise Wooden Block Set (100 pieces)",
        "slug": "rainbow-rise-wooden-block-set",
        "category_slug": "building-construction",
        "brand": "Maple & Moss",
        "price_cents": 4299,
        "stock_quantity": 64,
        "min_age_months": 24,
        "max_age_months": 96,
        "is_featured": True,
        "description": (
            "One hundred sanded beechwood blocks in eight shapes and six water-based "
            "colours, packed in a cotton drawstring bag. Heavy enough to stack tall, "
            "light enough for toddler hands, and the flat faces mean towers actually "
            "stay up long enough to knock down on purpose."
        ),
        "safety_notes": SAFETY_SMALL_PARTS,
    },
    {
        "name": "MagnaTile Explorer Starter Pack (72 pieces)",
        "slug": "magnatile-explorer-starter-pack",
        "category_slug": "building-construction",
        "brand": "BrightBuild",
        "price_cents": 5999,
        "stock_quantity": 48,
        "min_age_months": 36,
        "max_age_months": 120,
        "is_featured": True,
        "description": (
            "Translucent magnetic tiles in squares, triangles and arches that snap "
            "together into castles, cars and cathedrals. Riveted seams keep the "
            "magnets sealed, and the colours cast stained-glass shadows on a sunny "
            "floor."
        ),
        "safety_notes": SAFETY_SMALL_PARTS + " Contains magnets; seek medical help if swallowed.",
    },
    {
        "name": "Gravity Loop Marble Run (Deluxe)",
        "slug": "gravity-loop-marble-run-deluxe",
        "category_slug": "building-construction",
        "brand": "BrightBuild",
        "price_cents": 4799,
        "stock_quantity": 37,
        "min_age_months": 48,
        "max_age_months": 144,
        "is_featured": False,
        "description": (
            "A 118-piece run with two loops, a funnel, a see-saw drop and 20 glass "
            "marbles. Pieces click rather than balance, so a five-year-old can rebuild "
            "the whole track without an adult holding the middle."
        ),
        "safety_notes": SAFETY_SMALL_PARTS + " Marbles are a choking hazard for children under 5.",
    },
    {
        "name": "Junior Engineer Nuts & Bolts Workshop",
        "slug": "junior-engineer-nuts-bolts-workshop",
        "category_slug": "building-construction",
        "brand": "Tinker Crew",
        "price_cents": 3499,
        "stock_quantity": 55,
        "min_age_months": 36,
        "max_age_months": 96,
        "is_featured": False,
        "description": (
            "Chunky plastic nuts, bolts, plates and a child-safe ratcheting screwdriver "
            "that build into a helicopter, a dune buggy or whatever else turns up. "
            "Genuinely good practice for the pincer grip and for finishing what you start."
        ),
        "safety_notes": SAFETY_SMALL_PARTS,
    },
    {
        "name": "Castle Quest Brick Set (480 pieces)",
        "slug": "castle-quest-brick-set",
        "category_slug": "building-construction",
        "brand": "Blockworks",
        "price_cents": 6499,
        "stock_quantity": 26,
        "min_age_months": 72,
        "max_age_months": 168,
        "is_featured": False,
        "description": (
            "A drawbridge, four towers, a dragon and three minifigures across 480 "
            "compatible bricks. The instruction book has a second build on the back "
            "cover, which is where the real play starts."
        ),
        "safety_notes": SAFETY_SMALL_PARTS,
    },
    # --- Dolls & Plush ----------------------------------------------------
    {
        "name": "Bramble the Organic Cotton Bear",
        "slug": "bramble-organic-cotton-bear",
        "category_slug": "dolls-plush",
        "brand": "Hollow Hill",
        "price_cents": 2999,
        "stock_quantity": 88,
        "min_age_months": 0,
        "max_age_months": 96,
        "is_featured": True,
        "description": (
            "A 12-inch bear in GOTS-certified organic cotton with embroidered eyes, no "
            "beads, no plastic joints and a weighted bottom so he sits up next to a cot. "
            "Machine washable, which matters more than anything else on this list."
        ),
        "safety_notes": SAFETY_INFANT,
    },
    {
        "name": "Meadow Friends Rag Doll — Iris",
        "slug": "meadow-friends-rag-doll-iris",
        "category_slug": "dolls-plush",
        "brand": "Hollow Hill",
        "price_cents": 3299,
        "stock_quantity": 41,
        "min_age_months": 18,
        "max_age_months": 96,
        "is_featured": False,
        "description": (
            "A soft-bodied 15-inch doll with yarn hair that survives brushing, removable "
            "dungarees with real buttons, and boots that go back on without a fight."
        ),
        "safety_notes": SAFETY_INFANT,
    },
    {
        "name": "Little Kitchen Play Café Set",
        "slug": "little-kitchen-play-cafe-set",
        "category_slug": "dolls-plush",
        "brand": "Maple & Moss",
        "price_cents": 5499,
        "stock_quantity": 33,
        "min_age_months": 36,
        "max_age_months": 108,
        "is_featured": True,
        "description": (
            "A wooden café counter with a clicking espresso lever, 22 felt pastries, "
            "two mugs and an order pad. Pretend play with a queue, a menu and a till, "
            "which is to say hours of it."
        ),
        "safety_notes": SAFETY_SMALL_PARTS,
    },
    {
        "name": "Dreamlight Nursery Doll & Cot",
        "slug": "dreamlight-nursery-doll-cot",
        "category_slug": "dolls-plush",
        "brand": "Little Lane",
        "price_cents": 4499,
        "stock_quantity": 29,
        "min_age_months": 36,
        "max_age_months": 96,
        "is_featured": False,
        "description": (
            "A 14-inch baby doll with a folding wooden cot, quilt, bottle and a "
            "wind-up lullaby drum. The cot folds flat, which is the only reason it "
            "ever gets tidied away."
        ),
        "safety_notes": SAFETY_SMALL_PARTS,
    },
    {
        "name": "Pocket Pals Mini Plush Set (6 animals)",
        "slug": "pocket-pals-mini-plush-set",
        "category_slug": "dolls-plush",
        "brand": "Hollow Hill",
        "price_cents": 2199,
        "stock_quantity": 96,
        "min_age_months": 24,
        "max_age_months": 84,
        "is_featured": False,
        "description": (
            "Six four-inch animals — fox, otter, hedgehog, owl, badger and hare — in a "
            "mesh carry bag. Small enough for a coat pocket, sturdy enough for the wash."
        ),
        "safety_notes": SAFETY_INFANT,
    },
    # --- Games & Puzzles --------------------------------------------------
    {
        "name": "Woodland Match Memory Game",
        "slug": "woodland-match-memory-game",
        "category_slug": "games-puzzles",
        "brand": "Fox & Feather",
        "price_cents": 1799,
        "stock_quantity": 120,
        "min_age_months": 36,
        "max_age_months": 96,
        "is_featured": False,
        "description": (
            "Forty-eight thick board tiles with 24 illustrated woodland pairs. Plays in "
            "ten minutes, travels in a tin, and small children beat adults at it "
            "roughly every time."
        ),
        "safety_notes": SAFETY_SMALL_PARTS,
    },
    {
        "name": "Sunny Farm 48-Piece Floor Puzzle",
        "slug": "sunny-farm-floor-puzzle",
        "category_slug": "games-puzzles",
        "brand": "Fox & Feather",
        "price_cents": 1599,
        "stock_quantity": 84,
        "min_age_months": 36,
        "max_age_months": 84,
        "is_featured": False,
        "description": (
            "A two-foot farmyard scene in 48 chunky pieces cut for small hands, printed "
            "on recycled board with a matte finish that does not glare under a lamp."
        ),
        "safety_notes": SAFETY_SMALL_PARTS,
    },
    {
        "name": "Rocket Race Family Board Game",
        "slug": "rocket-race-family-board-game",
        "category_slug": "games-puzzles",
        "brand": "Tabletop Junior",
        "price_cents": 2899,
        "stock_quantity": 52,
        "min_age_months": 60,
        "max_age_months": 168,
        "is_featured": True,
        "description": (
            "A press-your-luck race to Jupiter for two to five players, 20 minutes a "
            "game. Simple enough for a six-year-old, sharp enough that the adults stop "
            "letting them win."
        ),
        "safety_notes": SAFETY_SMALL_PARTS,
    },
    {
        "name": "Story Cubes Adventure Dice",
        "slug": "story-cubes-adventure-dice",
        "category_slug": "games-puzzles",
        "brand": "Tabletop Junior",
        "price_cents": 1299,
        "stock_quantity": 143,
        "min_age_months": 48,
        "max_age_months": 168,
        "is_featured": False,
        "description": (
            "Nine picture dice, 54 images, no rules to speak of: roll them and tell the "
            "story you get. The best five-minute waiting-room toy on this site."
        ),
        "safety_notes": SAFETY_SMALL_PARTS,
    },
    {
        "name": "Deep Sea 200-Piece Jigsaw",
        "slug": "deep-sea-200-piece-jigsaw",
        "category_slug": "games-puzzles",
        "brand": "Fox & Feather",
        "price_cents": 1899,
        "stock_quantity": 61,
        "min_age_months": 84,
        "max_age_months": 168,
        "is_featured": False,
        "description": (
            "A 200-piece coral-reef scene with a species key on the back of the box, so "
            "the puzzle turns into a spotting game once it is finished."
        ),
        "safety_notes": SAFETY_SMALL_PARTS,
    },
    # --- Outdoor & Active Play -------------------------------------------
    {
        "name": "Trailblazer Wooden Balance Bike",
        "slug": "trailblazer-wooden-balance-bike",
        "category_slug": "outdoor-active-play",
        "brand": "Rove",
        "price_cents": 8999,
        "stock_quantity": 22,
        "min_age_months": 24,
        "max_age_months": 60,
        "is_featured": True,
        "description": (
            "A birch-ply balance bike with air tyres, an adjustable seat from 13 to 17 "
            "inches and a padded handlebar bumper. Skips stabilisers entirely; most "
            "children move straight to a pedal bike."
        ),
        "safety_notes": SAFETY_OUTDOOR,
    },
    {
        "name": "Backyard Bounce Jumbo Play Ball Set",
        "slug": "backyard-bounce-jumbo-play-ball-set",
        "category_slug": "outdoor-active-play",
        "brand": "Rove",
        "price_cents": 2499,
        "stock_quantity": 74,
        "min_age_months": 24,
        "max_age_months": 120,
        "is_featured": False,
        "description": (
            "Three textured playground balls in graded sizes with a hand pump and a "
            "mesh bag. Soft enough for indoors when the weather turns, which it will."
        ),
        "safety_notes": "Adult supervision recommended. Inflate to the printed pressure only.",
    },
    {
        "name": "Splash Zone Water Table",
        "slug": "splash-zone-water-table",
        "category_slug": "outdoor-active-play",
        "brand": "Sunbeam Play",
        "price_cents": 6799,
        "stock_quantity": 18,
        "min_age_months": 18,
        "max_age_months": 72,
        "is_featured": False,
        "description": (
            "A two-tier water table with a spinning wheel, a ramp, a drain plug and "
            "eight scoops and cups. Legs detach for storage; the whole thing empties "
            "from the side without tipping."
        ),
        "safety_notes": (
            "Drowning hazard: never leave a child unattended near water, even shallow. "
            "Empty the table after every use."
        ),
    },
    {
        "name": "Sidewalk Chalk Artist Kit (48 sticks)",
        "slug": "sidewalk-chalk-artist-kit",
        "category_slug": "outdoor-active-play",
        "brand": "Sunbeam Play",
        "price_cents": 1499,
        "stock_quantity": 110,
        "min_age_months": 36,
        "max_age_months": 144,
        "is_featured": False,
        "description": (
            "Forty-eight dustless chalk sticks in 12 colours with two stencils and a "
            "chalk holder that keeps hands clean. Washes off with a hose."
        ),
        "safety_notes": SAFETY_SMALL_PARTS,
    },
    {
        "name": "Junior Archery Target Set (foam-tipped)",
        "slug": "junior-archery-target-set",
        "category_slug": "outdoor-active-play",
        "brand": "Rove",
        "price_cents": 3799,
        "stock_quantity": 31,
        "min_age_months": 72,
        "max_age_months": 168,
        "is_featured": False,
        "description": (
            "A 24-inch draw bow with five foam-tipped arrows, a quiver and a "
            "free-standing target with a scoring ring. Low draw weight, real technique."
        ),
        "safety_notes": (
            "Never aim at people or animals. Eye-injury risk. Adult supervision "
            "required at all times."
        ),
    },
    # --- STEM & Learning --------------------------------------------------
    {
        "name": "CodeBot Screen-Free Coding Robot",
        "slug": "codebot-screen-free-coding-robot",
        "category_slug": "stem-learning",
        "brand": "Tinker Crew",
        "price_cents": 7999,
        "stock_quantity": 24,
        "min_age_months": 48,
        "max_age_months": 120,
        "is_featured": True,
        "description": (
            "A programmable robot driven by physical instruction tiles rather than an "
            "app: sequence, loop, debug, run. Rechargeable, 4 hours of play per charge, "
            "no screen anywhere in the box."
        ),
        "safety_notes": SAFETY_ELECTRONIC,
    },
    {
        "name": "Volcano & Crystal Science Lab",
        "slug": "volcano-crystal-science-lab",
        "category_slug": "stem-learning",
        "brand": "Tinker Crew",
        "price_cents": 3299,
        "stock_quantity": 47,
        "min_age_months": 72,
        "max_age_months": 156,
        "is_featured": False,
        "description": (
            "Fifteen experiments including a repeatable volcano, a crystal garden that "
            "grows over three days, and a 32-page lab book with a hypothesis box on "
            "every page."
        ),
        "safety_notes": (
            "Contains chemicals. Adult supervision required. Wear the supplied goggles. "
            "Keep away from children under 6."
        ),
    },
    {
        "name": "Stargazer Beginner Telescope",
        "slug": "stargazer-beginner-telescope",
        "category_slug": "stem-learning",
        "brand": "Northlight",
        "price_cents": 9499,
        "stock_quantity": 15,
        "min_age_months": 96,
        "max_age_months": 192,
        "is_featured": True,
        "description": (
            "A 70mm refractor on an aluminium tripod with two eyepieces, a finder "
            "scope and a moon filter. Genuinely shows the craters and Jupiter's four "
            "brightest moons — not a toy pretending to be a telescope."
        ),
        "safety_notes": (
            "Never look at the sun through this telescope or its finder. Permanent "
            "blindness can result. Adult supervision required."
        ),
    },
    {
        "name": "Alphabet Adventure Magnetic Letters",
        "slug": "alphabet-adventure-magnetic-letters",
        "category_slug": "stem-learning",
        "brand": "Little Lane",
        "price_cents": 2299,
        "stock_quantity": 92,
        "min_age_months": 36,
        "max_age_months": 84,
        "is_featured": False,
        "description": (
            "Uppercase and lowercase magnetic letters plus 30 phonics cards and a "
            "magnetic board. Vowels are colour-coded, which quietly does half the "
            "teaching for you."
        ),
        "safety_notes": SAFETY_SMALL_PARTS + " Contains magnets; seek medical help if swallowed.",
    },
]
