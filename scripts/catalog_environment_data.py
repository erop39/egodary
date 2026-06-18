"""Environment catalog subgroup definitions for environment_pack tags."""

ENVIRONMENT_FIELD_LABELS: dict[str, str] = {
    "location": "Location",
    "situation": "Scene / Situation",
    "modifiers": "Atmospheric Modifiers",
}

ENVIRONMENT_SUBGROUP_LABELS: dict[str, dict[str, str]] = {
    "location": {
        "indoor": "Indoor",
        "outdoor_semi": "Outdoor & Semi-Outdoor",
        "fantasy_stylized": "Fantasy & Stylized",
    },
    "modifiers": {
        "atmospheric": "Atmospheric Modifiers",
    },
    "situation": {
        "pressed_cornered": "Pressed / Cornered",
        "interacting_objects": "Interacting with Environment / Objects",
        "restrained_captured": "Restrained / Captured",
        "dynamic_action": "Dynamic / Action Scenes",
        "intimate_fetish": "Intimate / Fetish Scenes",
    },
}

ENVIRONMENT_CATALOG: dict[str, dict[str, list[str]]] = {
    "location": {
        "indoor": [
            "Modern bedroom",
            "Luxury bedroom",
            "Minimalist apartment",
            "Dark moody bedroom",
            "Hotel room",
            "Penthouse",
            "Basement / dungeon",
            "Abandoned building interior",
            "Neon-lit room",
            "Candlelit room",
            "Bathroom (wet tiles)",
            "Kitchen counter",
            "Living room couch",
            "Mirror room",
            "Red light district room",
        ],
        "outdoor_semi": [
            "Night city street",
            "Rooftop at night",
            "Alleyway",
            "Forest at night",
            "Beach at night",
            "Car interior (night)",
            "Balcony",
            "Abandoned warehouse",
            "Under bridge",
            "Neon cyberpunk street",
        ],
        "fantasy_stylized": [
            "Dark fantasy bedroom",
            "Throne room",
            "Gothic castle interior",
            "Futuristic bedroom",
            "Void / abstract background",
            "Heavenly / ethereal space",
            "Underground club",
            "Luxury BDSM club",
            "Rainy window background",
            "Foggy atmosphere",
        ],
    },
    "situation": {
        "pressed_cornered": [
            "Backed against a wall / bulkhead",
            "Pressed flat against surface",
            "Cornered / Pinned to the wall",
            "Trapped between objects",
        ],
        "interacting_objects": [
            "Robotic arms moving around her",
            "Avoid moving machinery",
            "Interacting with consoles / machinery",
            "Leaning against bulkhead",
            "Pressed to the glass/window",
        ],
        "restrained_captured": [
            "Mechanically restrained",
            "Tied / bound to structure",
            "Held by robotic arms",
            "Suspended",
        ],
        "dynamic_action": [
            "Dodging / Evading",
            "Running through environment",
            "Hiding",
            "Searching / Investigating",
        ],
        "intimate_fetish": [
            "Pressed against someone/something",
            "Pinned down",
            "Lifted / Carried",
            "Forced against surface",
        ],
    },
    "modifiers": {
        "atmospheric": [
            "Heavy fog",
            "Light rain",
            "Neon reflections",
            "Volumetric light rays",
            "Smoke / haze",
            "Wet surfaces",
            "Reflections on floor/walls",
        ],
    },
}

# Location groups for conflict matching (resolved to ids at build time)
ENVIRONMENT_LOCATION_GROUPS: dict[str, list[str]] = {
    "dark_moody": [
        "Dark moody bedroom",
        "Basement / dungeon",
        "Abandoned building interior",
        "Alleyway",
        "Forest at night",
        "Under bridge",
        "Gothic castle interior",
        "Underground club",
        "Void / abstract background",
        "Foggy atmosphere",
    ],
    "luxury": [
        "Luxury bedroom",
        "Penthouse",
        "Hotel room",
        "Luxury BDSM club",
    ],
    "neon_cyberpunk": [
        "Neon-lit room",
        "Neon cyberpunk street",
        "Futuristic bedroom",
    ],
    "dungeon": [
        "Basement / dungeon",
        "Luxury BDSM club",
        "Gothic castle interior",
    ],
    "gentle_romantic": [
        "Candlelit room",
        "Heavenly / ethereal space",
        "Rainy window background",
        "Modern bedroom",
        "Living room couch",
    ],
    "abandoned": [
        "Abandoned building interior",
        "Abandoned warehouse",
    ],
    "indoor": [
        "Modern bedroom",
        "Luxury bedroom",
        "Minimalist apartment",
        "Dark moody bedroom",
        "Hotel room",
        "Penthouse",
        "Basement / dungeon",
        "Abandoned building interior",
        "Neon-lit room",
        "Candlelit room",
        "Bathroom (wet tiles)",
        "Kitchen counter",
        "Living room couch",
        "Mirror room",
        "Red light district room",
    ],
}

ENVIRONMENT_COMPAT_WARNINGS: list[dict] = [
    {
        "message": "Luxury location clashes with heavy BDSM / dungeon fetish elements.",
        "location_group": "luxury",
        "fetish_group": "heavy_bdsm",
        "fetish_min_level": 4,
    },
    {
        "message": "Neon cyberpunk environment may fight gentle romantic expressions.",
        "location_group": "neon_cyberpunk",
        "face_expression_group": "gentle_romantic",
    },
    {
        "message": "Abandoned setting with bright studio lighting may look incoherent.",
        "location_group": "abandoned",
        "light_type_labels": ["Soft studio lighting", "Hard studio lighting"],
    },
    {
        "message": "Dungeon location with high key lighting rarely reads well.",
        "location_group": "dungeon",
        "light_type_labels": ["High key lighting"],
    },
]
