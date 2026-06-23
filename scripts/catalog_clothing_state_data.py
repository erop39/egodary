"""Universal clothing state modifiers — bound to the garment tag in each outfit slot."""

CLOTHING_STATE_DIMENSIONS: dict[str, str] = {
    "moisture": "Moisture & Wetness",
    "damage": "Damage & Wear",
    "transparency": "Transparency & Sheerness",
    "fit": "Fit & Tension",
    "disorder": "Disorder & Messiness",
    "partial_removal": "Partial Removal & Exposure",
    "stains": "Stains & Fluids",
    "color": "Color",
    "extra": "Additional states",
}

# dimension -> list of (id_suffix, label, modifier_phrase)
# Phrases are short modifiers prepended to the slot garment tag (no generic "clothing").
CLOTHING_STATE_ITEMS: dict[str, list[tuple[str, str, str]]] = {
    "moisture": [
        ("wet_soaked", "Wet / Soaked", "wet soaked"),
        ("damp", "Damp", "damp"),
        ("sweat_soaked", "Sweat-soaked", "sweat-soaked"),
        ("water_droplets", "Water droplets", "water droplets on"),
    ],
    "damage": [
        ("torn_ripped", "Torn / Ripped", "torn ripped"),
        ("slightly_torn", "Slightly torn", "slightly torn"),
        ("heavily_damaged", "Heavily damaged", "heavily damaged"),
        ("frayed", "Frayed", "frayed"),
        ("holes", "Holes", "with holes"),
    ],
    "transparency": [
        ("see_through", "See-through", "see-through"),
        ("wet_see_through", "Wet see-through", "wet see-through"),
        ("sheer_translucent", "Sheer / Translucent", "sheer translucent"),
        ("partially_transparent", "Partially transparent", "partially transparent"),
    ],
    "fit": [
        ("tight_skin_tight", "Tight / Skin-tight", "tight skin-tight"),
        ("stretched_strained", "Stretched / Strained", "stretched strained"),
        ("clinging", "Clinging", "clinging"),
        ("baggy_loose", "Baggy / Loose", "baggy loose"),
    ],
    "disorder": [
        ("disheveled_messy", "Disheveled / Messy", "disheveled messy"),
        ("rumpled_wrinkled", "Rumpled / Wrinkled", "rumpled wrinkled"),
        ("half_undone", "Half-undone", "half-undone"),
        ("slipping_off", "Slipping off", "slipping off"),
    ],
    "partial_removal": [
        ("partially_removed", "Partially removed", "partially removed"),
        ("pulled_down", "Pulled down", "pulled down"),
        ("pulled_up", "Pulled up", "pulled up"),
        ("open_unbuttoned", "Open / Unbuttoned", "open unbuttoned"),
        ("slid_off_shoulders", "Slid off shoulders", "slid off shoulders"),
    ],
    "stains": [
        ("cum_stained", "Cum-stained", "cum-stained"),
        ("sweat_stained", "Sweat-stained", "sweat-stained"),
        ("wet_with_fluids", "Wet with fluids", "wet with fluids"),
        ("stained", "Stained", "stained"),
        ("soiled", "Soiled", "soiled"),
    ],
    "color": [
        # Classic colors (always best-sellers)
        ("black", "Black", "black"),
        ("white", "White", "white"),
        ("beige", "Beige", "beige"),
        ("grey", "Grey", "grey"),
        ("navy_blue", "Navy Blue", "navy blue"),
        ("brown", "Brown", "brown"),
        ("red", "Red", "red"),
        ("pink", "Pink", "pink"),
        ("camel", "Camel", "camel"),
        ("burgundy", "Burgundy", "burgundy"),
        # Trending / very popular colors (2025-2026)
        ("olive_green", "Olive Green", "olive green"),
        ("sage_green", "Sage Green", "sage green"),
        ("dusty_rose", "Dusty Rose", "dusty rose"),
        ("blush_pink", "Blush Pink", "blush pink"),
        ("chocolate_brown", "Chocolate Brown", "chocolate brown"),
        ("lavender", "Lavender", "lavender"),
        ("terracotta", "Terracotta", "terracotta"),
        ("butter_yellow", "Butter Yellow", "butter yellow"),
        ("powder_blue", "Powder Blue", "powder blue"),
        ("emerald_green", "Emerald Green", "emerald green"),
        ("rust", "Rust", "rust"),
        ("mocha", "Mocha", "mocha"),
        # Additional
        ("charcoal_grey", "Charcoal Grey", "charcoal grey"),
        ("ivory", "Ivory", "ivory"),
        ("hot_pink", "Hot Pink", "hot pink"),
        ("wine_red", "Wine Red", "wine red"),
    ],
    "extra": [
        ("glowing_neon", "Glowing / Neon", "glowing neon"),
        ("oil_shiny", "Oil / Shiny", "oil shiny"),
        ("glued_stuck", "Glued / Stuck", "glued stuck"),
        ("floating_flowing", "Floating / Flowing", "flowing"),
    ],
}
