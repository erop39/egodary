"""Lighting catalog subgroup definitions for lighting_pack tags."""

LIGHTING_FIELD_LABELS: dict[str, str] = {
    "light_type": "Light Type / Source",
    "direction": "Lighting Direction",
    "quality": "Lighting Quality",
    "color_mood": "Color Temperature & Mood",
    "nsfw": "NSFW / Erotic Lighting",
}

LIGHTING_SUBGROUP_LABELS: dict[str, dict[str, str]] = {
    "light_type": {
        "natural": "Natural Light",
        "artificial": "Artificial Light",
        "dramatic_cinematic": "Dramatic & Cinematic",
    },
    "direction": {
        "basic": "Basic Directions",
        "advanced_erotic": "Advanced & Erotic Directions",
    },
    "quality": {
        "soft_hard": "Soft vs Hard",
        "special": "Special Qualities",
    },
    "color_mood": {
        "warm": "Warm Lighting",
        "cool": "Cool Lighting",
        "colored_stylized": "Colored & Stylized",
    },
    "nsfw": {
        "body_highlight": "Highlighting the Body",
        "atmospheric_intimate": "Atmospheric & Intimate",
        "special_effects": "Special Effects",
    },
}

LIGHTING_CATALOG: dict[str, dict[str, list[str]]] = {
    "light_type": {
        "natural": [
            "Natural daylight",
            "Soft window light",
            "Golden hour lighting",
            "Blue hour lighting",
            "Overcast soft light",
            "Sunlight through curtains",
            "Dappled sunlight",
        ],
        "artificial": [
            "Soft studio lighting",
            "Hard studio lighting",
            "Neon lighting",
            "LED strip lighting",
            "Candlelight",
            "Lamp light / bedside lamp",
            "Streetlight at night",
            "Fluorescent lighting",
        ],
        "dramatic_cinematic": [
            "Dramatic cinematic lighting",
            "Low key lighting",
            "High key lighting",
            "Volumetric lighting",
            "God rays / crepuscular rays",
        ],
    },
    "direction": {
        "basic": [
            "Front lighting",
            "Side lighting",
            "Back lighting",
            "Top lighting (from above)",
            "Bottom lighting (from below)",
        ],
        "advanced_erotic": [
            "Strong side lighting (dramatic shadows)",
            "Rim lighting",
            "Edge lighting",
            "Backlit silhouette",
            "Three-quarter lighting",
            "Split lighting (half face in shadow)",
            "Butterfly lighting",
            "Loop lighting",
            "Rembrandt lighting",
            "Underlighting (from below — unsettling / erotic)",
        ],
    },
    "quality": {
        "soft_hard": [
            "Soft diffused light",
            "Hard direct light",
            "Very soft gentle light",
            "Harsh dramatic light",
            "Moody soft shadows",
        ],
        "special": [
            "Cinematic soft lighting",
            "High contrast lighting",
            "Low contrast lighting",
            "Glowing / ethereal light",
            "Hazy / atmospheric light",
            "Sharp shadows",
            "Soft shadows",
            "Volumetric god rays",
            "Crepuscular rays",
            "Subtle rim light",
        ],
    },
    "color_mood": {
        "warm": [
            "Warm golden lighting",
            "Warm orange lighting",
            "Candlelight / fireplace",
            "Sunset lighting",
            "Cozy warm light",
        ],
        "cool": [
            "Cool blue lighting",
            "Cold moonlight",
            "Neon blue and pink",
            "Cyberpunk neon lighting",
            "Cold sterile light",
        ],
        "colored_stylized": [
            "Red lighting (passionate / dangerous)",
            "Purple / magenta lighting",
            "Pink neon lighting",
            "Green neon lighting",
            "RGB / multicolored lighting",
            "Blacklight / UV lighting",
            "Moody teal and orange",
            "Dramatic red and black",
        ],
    },
    "nsfw": {
        "body_highlight": [
            "Rim lighting on body curves",
            "Side lighting emphasizing breasts",
            "Back lighting on silhouette",
            "Light highlighting thighs and legs",
            "Dramatic lighting on ass",
            "Light and shadow on cleavage",
        ],
        "atmospheric_intimate": [
            "Low key intimate lighting",
            "Candlelit erotic atmosphere",
            "Moody bedroom lighting",
            "Neon erotic lighting",
            "Volumetric light in dark room",
            "Light rays through smoke/haze",
            "Soft glowing skin lighting",
            "Wet skin with strong highlights",
            "High contrast erotic lighting",
        ],
        "special_effects": [
            "Light leaking through curtains",
            "Blinds shadow pattern on body",
            "Mirror reflection with lighting",
            "Strong backlight creating halo",
            "Dramatic underlighting on face and body",
        ],
    },
}

LIGHTING_PRESETS: list[dict[str, str]] = [
    {
        "id": "intimate_erotica",
        "label": "Интимная эротика",
        "hint": "Low key + Rim + Candlelight + Close-Up",
        "light_type": "Low key lighting",
        "direction": "Rim lighting",
        "color_mood": "Candlelight / fireplace",
        "framing": "Close-Up",
    },
    {
        "id": "dominant_view",
        "label": "Доминирующий вид",
        "hint": "Dramatic cinematic + Low Angle + Strong side",
        "light_type": "Dramatic cinematic lighting",
        "direction": "Strong side lighting (dramatic shadows)",
        "angle": "Low Angle",
    },
    {
        "id": "gentle_romantic",
        "label": "Нежная / романтичная",
        "hint": "Soft window + Golden hour + Eye Level",
        "light_type": "Soft window light",
        "color_mood": "Warm golden lighting",
        "angle": "Eye Level",
    },
    {
        "id": "cyberpunk_neon",
        "label": "Киберпанк / неон",
        "hint": "Neon + Dutch Angle + High contrast",
        "light_type": "Neon lighting",
        "quality": "High contrast lighting",
        "color_mood": "Cyberpunk neon lighting",
        "angle": "Dutch Angle",
    },
    {
        "id": "strong_sexuality",
        "label": "Сильная сексуальность",
        "hint": "Back + Rim + Low key + Cowboy Shot",
        "light_type": "Low key lighting",
        "direction": "Back lighting",
        "quality": "Subtle rim light",
        "nsfw": "Back lighting on silhouette",
        "framing": "Cowboy Shot (thighs)",
    },
]

# Cross-field mood / style hints (resolved to ids at build time)
LIGHTING_COMPAT_WARNINGS: list[dict] = [
    {
        "message": "Neon light with warm candle tones may look incoherent.",
        "light_type_labels": ["Neon lighting", "LED strip lighting"],
        "color_mood_labels": [
            "Candlelight / fireplace",
            "Cozy warm light",
            "Warm golden lighting",
        ],
    },
    {
        "message": "High key lighting suits lighter romantic moods — intense erotic NSFW lighting may clash.",
        "light_type_labels": ["High key lighting"],
        "nsfw_labels": ["High contrast erotic lighting", "Neon erotic lighting"],
    },
    {
        "message": "Volumetric light works best with hazy, moody, or dark-room atmosphere.",
        "light_type_labels": ["Volumetric lighting", "God rays / crepuscular rays"],
        "quality_labels": ["Glowing / ethereal light", "Soft shadows"],
    },
    {
        "message": "Cool blue mood with warm candlelight type may fight each other.",
        "light_type_labels": ["Candlelight"],
        "color_mood_labels": ["Cool blue lighting", "Cold moonlight", "Cold sterile light"],
    },
    {
        "message": "Rim / edge direction excels with body-focused or silhouette framing.",
        "direction_labels": ["Rim lighting", "Edge lighting", "Backlit silhouette"],
    },
    {
        "message": "Underlighting creates an unsettling or intensely erotic effect.",
        "direction_labels": ["Underlighting (from below — unsettling / erotic)"],
    },
]
