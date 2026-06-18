"""Fetish element catalog for fetish_pack tags."""

FETISH_GROUP_LABELS: dict[str, str] = {
    "bdsm_restraints": "BDSM & Restraints",
    "toys_accessories": "Toys & Accessories",
    "body_marks": "Body Marks & Traces",
    "fluids_wetness": "Fluids & Wetness",
    "body_writing": "Body Writing & Humiliation",
    "specific_details": "Specific Fetish Details",
    "advanced_heavy": "Advanced / Heavy Fetish",
}

FETISH_CATALOG: dict[str, list[str]] = {
    "bdsm_restraints": [
        "Leather cuffs",
        "Metal handcuffs",
        "Rope bondage (shibari)",
        "Silk ropes",
        "Collar and leash",
        "Ball gag",
        "Bit gag",
        "Blindfold",
        "Spreader bar",
        "Chains",
        "Harness restraints",
        "Suspension ropes",
    ],
    "toys_accessories": [
        "Vibrator",
        "Dildo",
        "Butt plug",
        "Nipple clamps",
        "Wand vibrator",
        "Riding crop",
        "Paddle",
        "Whip",
        "Flogger",
        "Anal hook",
    ],
    "body_marks": [
        "Hickeys on neck",
        "Bite marks",
        "Handprints on ass/thighs",
        "Rope marks on skin",
        "Red marks from spanking",
        "Light bruises",
        "Lipstick marks on body",
        "Sweat trails",
    ],
    "fluids_wetness": [
        "Saliva on lips and chin",
        "Drooling",
        "Sweat on skin",
        "Wet skin (water/oil)",
        "Cum on body/face",
        "Cum on lips/tongue",
        "Ahegao with drool",
        "Wet pussy (visible arousal)",
    ],
    "body_writing": [
        'Body writing ("slut", "cumdump", etc.)',
        "Lipstick writing on body",
        "Marker on skin",
        '"Property of..." text',
    ],
    "specific_details": [
        "Ahegao face",
        "Heart-shaped pupils",
        "Broken expression",
        "Mind break",
        "Excessive fluids",
        "Used / messy look",
        "Aftercare elements",
        "Post-sex glow and mess",
    ],
    "advanced_heavy": [
        "Full body harness",
        "Latex catsuit (if not in outfit)",
        "Gas mask",
        "Pet play elements (ears, tail, collar)",
        "Medical play elements",
        "Sensory deprivation",
        "Wax play marks",
        "Electro play elements (light)",
    ],
}

FETISH_CONFLICT_GROUPS: list[list[str]] = [
    ["Ball gag", "Bit gag"],
    ["Blindfold", "Sensory deprivation"],
]

FETISH_COMPAT_WARNINGS: list[dict] = [
    {
        "message": "Mind break and aftercare elements tell opposite emotional stories.",
        "labels": ["Mind break", "Aftercare elements"],
    },
    {
        "message": "Full body harness overlaps with harness restraints — may look redundant.",
        "labels": ["Full body harness", "Harness restraints"],
    },
    {
        "message": "Collar and leash partially overlaps with pet play accessories.",
        "labels": ["Collar and leash", "Pet play elements (ears, tail, collar)"],
    },
    {
        "message": "Ahegao face may duplicate face-expression ahegao if both are set.",
        "labels": ["Ahegao face"],
    },
]
