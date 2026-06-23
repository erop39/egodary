"""Character body catalog — source data for character_pack."""

CHARACTER_FIELD_LABELS: dict[str, str] = {
    "age_appearance": "Age Appearance",
    "body_type": "Body Type",
    "breast_size": "Breast Size",
    "breast_shape": "Breast Shape",
    "waist": "Waist",
    "hips_ass": "Hips & Ass",
    "legs": "Legs",
    "overall_figure": "Overall Figure",
    "height_build": "Height & Stature",
    "ethnicity": "Ethnicity",
    "skin_tone": "Skin Tone",
    "body_details": "Body Details",
}

CHARACTER_SUBGROUP_LABELS: dict[str, dict[str, str]] = {
    "age_appearance": {"ranges": "Visual Age"},
    "body_type": {"types": "Body Type"},
    "breast_size": {"sizes": "Breast Size"},
    "breast_shape": {"shapes": "Breast Shape"},
    "waist": {"waist": "Waist"},
    "hips_ass": {"hips": "Hips & Ass"},
    "legs": {"legs": "Legs"},
    "overall_figure": {"figure": "Overall Figure"},
    "height_build": {"stature": "Height & Stature"},
    "ethnicity": {"ethnicity": "Ethnicity"},
    "skin_tone": {"tone": "Skin Tone"},
    "body_details": {
        "skin_texture": "Skin Texture",
        "skin_details": "Skin Details",
        "body_details": "Body Details",
    },
}

CHARACTER_CATALOG: dict[str, dict[str, list[str]]] = {
    "age_appearance": {
        "ranges": [
            "18–20 (young adult)",
            "21–25",
            "26–30",
            "31–35",
            "36–40",
            "Mature beauty (35–45)",
            "MILF appearance",
            "Ageless / Timeless beauty",
        ],
    },
    "body_type": {
        "types": [
            "Slim / Slender",
            "Petite",
            "Athletic / Toned",
            "Fit",
            "Curvy",
            "Voluptuous",
            "Hourglass figure",
            "Slim-thick",
            "Soft / Chubby",
            "Muscular feminine",
            "Tall and elegant",
            "Shortstack",
        ],
    },
    "breast_size": {
        "sizes": [
            "Small breasts",
            "Medium breasts",
            "Large breasts",
            "Very large breasts",
            "Huge breasts",
        ],
    },
    "breast_shape": {
        "shapes": [
            "Perky breasts",
            "Round breasts",
            "Teardrop breasts",
            "Full breasts",
            "Heavy breasts",
            "Natural breasts",
            "Firm breasts",
            "Soft breasts",
        ],
    },
    "waist": {
        "waist": [
            "Slim waist",
            "Narrow waist",
            "Soft waist",
            "Toned waist",
            "Defined waist",
        ],
    },
    "hips_ass": {
        "hips": [
            "Wide hips",
            "Thick thighs",
            "Big ass",
            "Round ass",
            "Heart-shaped ass",
            "Bubble butt",
            "Plump ass",
            "Firm ass",
            "Soft ass",
            "Jiggly ass",
        ],
    },
    "legs": {
        "legs": [
            "Long legs",
            "Toned legs",
            "Thick thighs",
            "Slim legs",
            "Muscular legs",
            "Soft legs",
            "Long and elegant legs",
            "Short and thick legs",
            "Thigh gap",
            "Strong calves",
            "Smooth legs",
            "Legs with subtle muscle definition",
        ],
    },
    "overall_figure": {
        "figure": [
            "Hourglass proportions",
            "Curvy proportions",
            "Balanced proportions",
            "Pear-shaped figure",
            "Voluptuous lower body",
            "Athletic proportions",
        ],
    },
    "height_build": {
        "stature": [
            "Very short / Petite",
            "Short",
            "Average height",
            "Tall",
            "Very tall",
            "Shortstack (short + curvy)",
            "Tall and slender",
            "Tall and voluptuous",
            "Compact and curvy",
        ],
    },
    "ethnicity": {
        "ethnicity": [
            "Caucasian",
            "East Asian",
            "Southeast Asian",
            "South Asian",
            "Latina",
            "Black / African",
            "Mixed",
            "Arab / Middle Eastern",
            "Mediterranean",
            "Slavic",
            "Nordic",
            "Eurasian",
        ],
    },
    "skin_tone": {
        "tone": [
            "Fair / Porcelain",
            "Light beige",
            "Warm tan",
            "Golden / Olive",
            "Tan",
            "Deep tan",
            "Dark / Ebony",
            "Pale with pink undertones",
        ],
    },
    "body_details": {
        "skin_texture": [
            "Smooth flawless skin",
            "Soft skin",
            "Silky skin",
            "Toned skin",
            "Dewy / glowing skin",
            "Glowing skin",
            "Oily shiny skin",
            "Matte skin",
            "Wet skin (water/oil)",
            "Light sweat",
            "Slightly sweaty skin",
            "Glass skin effect",
            "Soft natural skin with pores",
        ],
        "skin_details": [
            "Light freckles across nose and cheeks",
            "Heavy freckles",
            "Beauty marks / moles",
            "Subtle blush on cheeks",
            "Heavy blush (aroused)",
            "Redness around mouth and cheeks",
            "Visible veins (subtle)",
            "Light scars",
            "Skin with goosebumps",
            "Wet skin with water droplets",
            "Sensitive skin",
            "Easily flushed skin",
        ],
        "body_details": [
            "Light freckles on body",
            "Subtle stretch marks",
            "Light cellulite",
            "Subtle muscle definition",
            "Soft stomach",
            "Toned stomach",
        ],
    },
}

CHARACTER_TREE_GROUPS: list[dict] = [
    {"field": "age_appearance", "label": "Age Appearance"},
    {"field": "body_type", "label": "Body Type"},
    {
        "label": "Body Proportions",
        "children": [
            {"field": "breast_size", "label": "Breast Size"},
            {"field": "breast_shape", "label": "Breast Shape"},
            {"field": "waist", "label": "Waist"},
            {"field": "hips_ass", "label": "Hips & Ass"},
            {"field": "legs", "label": "Legs"},
            {"field": "overall_figure", "label": "Overall Figure"},
        ],
    },
    {"field": "height_build", "label": "Height & Stature"},
    {
        "label": "Ethnicity & Skin Tone",
        "children": [
            {"field": "ethnicity", "label": "Ethnicity"},
            {"field": "skin_tone", "label": "Skin Tone"},
            {
                "field": "body_details",
                "label": "Skin Texture",
                "multi": True,
                "subgroup": "skin_texture",
            },
            {
                "field": "body_details",
                "label": "Skin Details",
                "multi": True,
                "subgroup": "skin_details",
            },
            {
                "field": "body_details",
                "label": "Body Details",
                "multi": True,
                "subgroup": "body_details",
            },
        ],
    },
]

# Tags that may appear in more than one field — pipeline dedupes by normalized tag text.
CHARACTER_DEDUPE_TAG_HINTS: frozenset[str] = frozenset(
    {
        "thick thighs",
        "shortstack",
        "matte skin",
        "beauty marks / moles",
    }
)
